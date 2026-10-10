# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .notify_mixin import DEFAULT_STUCK_REMINDER_DAYS, STUCK_REMINDER_DAYS_PARAM


class HrApplicant(models.Model):
    _name = 'hr.applicant'
    _inherit = ['hr.applicant', 'recruitment.notify.mixin']
    _rn_kind = 'stuck'
    _rn_action = 'hr_recruitment.crm_case_categ0_act_job'

    # When the candidate entered their current stage. Not the native
    # date_last_stage_update, which also moves whenever the kanban status dot
    # is changed - so a candidate could look freshly moved without having
    # moved at all.
    x_stage_entered_date = fields.Datetime(
        string='Entered Stage On', readonly=True, copy=False,
        default=fields.Datetime.now, index=True,
        help='When the candidate moved into their current stage.',
    )
    # Days-in-stage mark of the last stuck reminder sent. Zero means none
    # yet; a change of stage resets it, so each stage starts its own sequence.
    x_stage_reminder_sent_days = fields.Integer(
        string='Stuck Reminder Sent At', readonly=True, copy=False,
    )

    def write(self, vals):
        if 'stage_id' in vals and any(app.stage_id.id != vals['stage_id'] for app in self):
            vals = dict(vals)
            vals.setdefault('x_stage_entered_date', fields.Datetime.now())
            vals.setdefault('x_stage_reminder_sent_days', 0)
        return super().write(vals)

    # ── Email notifications ───────────────────────────────────────
    def _rn_assigned_users(self):
        """The candidate's Recruiter and the role's Recruitment Manager."""
        return self.user_id | self.job_id.user_id

    def _rn_details(self):
        self.ensure_one()
        app = self.sudo()
        activity = app.activity_ids.sorted(lambda a: (a.date_deadline, a.id))[:1]
        return {
            'name': app.partner_name or app.display_name or '',
            'role': app.job_id.name or '',
            'req_id': app.job_id.x_req_id or '',
            'client': app.department_id.name or '',
            'stage': app.stage_id.name or '',
            'recruiter': app.user_id.name or '',
            'manager': app.job_id.user_id.name or '',
            'contact': ' | '.join(p for p in (app.email_from, app.partner_phone) if p),
            'experience': f'{self._rn_number(app.x_total_experience)} yrs' if app.x_total_experience else '',
            'notice': self._rn_format_value('x_notice_period', app.x_notice_period)
                      if app.x_notice_period else '',
            'next_activity': ' - '.join(p for p in (
                activity.activity_type_id.name, activity.summary,
                self._rn_date(activity.date_deadline)) if p) if activity else '',
            'created_by': app.create_uid.name or '',
            'created_on': self._rn_local_date(app.create_date),
        }

    @api.model
    def _get_stuck_reminder_days(self):
        """Days marks switched on, most distant first. Only a parameter that
        does not exist at all takes the default: an empty one means every
        chip was cleared in the settings, and nothing is sent."""
        raw = self.env['ir.config_parameter'].sudo()._get_param(STUCK_REMINDER_DAYS_PARAM)
        if raw is None:
            raw = DEFAULT_STUCK_REMINDER_DAYS
        days = {int(c) for c in (raw or '').replace(' ', '').split(',') if c.isdigit() and int(c) > 0}
        return sorted(days, reverse=True)

    @api.model
    def _cron_send_stuck_candidate_reminders(self):
        """Remind about candidates sitting in one stage. Runs nightly.

        A mark is reached once the candidate has been in their stage that
        many days or more. The one sent is the furthest mark reached, and only
        if it is further than what already went out - so a repeated run is a
        no-op, and after downtime one reminder catches up rather than a
        backlog of them. Refused, archived and hired candidates are skipped,
        and so is any stage with reminders switched off.
        """
        if not self._rn_enabled('stuck'):
            return True
        days = self._get_stuck_reminder_days()
        if not days:
            return True
        today = fields.Date.context_today(self)
        candidates = self.search([
            ('application_status', '=', 'ongoing'),
            ('stage_id.x_stage_reminders', '=', True),
            ('x_stage_entered_date', '<=', fields.Datetime.subtract(
                fields.Datetime.now(), days=min(days))),
        ])
        for app in candidates:
            entered = fields.Datetime.context_timestamp(app, app.x_stage_entered_date).date()
            in_stage = (today - entered).days
            reached = [d for d in days if in_stage >= d]
            if not reached:
                continue
            mark = max(reached)
            if mark <= app.x_stage_reminder_sent_days:
                continue
            later = [d for d in days if d > in_stage]
            next_mark = min(later) if later else 0
            sent = app._rn_send(
                'recruitment_pipeline_report.mail_template_rp_stuck_candidate',
                app._rn_partners('stuck'),
                {'rn_stuck': {
                    'days': in_stage,
                    'accent': '#C0392B' if in_stage >= 14 else '#D68910',
                    'entered_on': self._rn_date(entered, 'EEEE, d MMMM y'),
                    'next_mark': next_mark,
                    'next_on': self._rn_date(fields.Date.add(entered, days=next_mark))
                               if next_mark else '',
                }},
            )
            if sent:
                # Not tracked, so this write sends nothing of its own.
                app.x_stage_reminder_sent_days = mark
        return True
