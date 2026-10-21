# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .crm_lead import (
    ACTIVITY_REMINDER_DAYS_PARAM, DEFAULT_INACTIVITY_REPORT_MIN_DAYS, DEFAULT_REPORT_MONTHDAY,
    DEFAULT_REPORT_PERIOD, DEFAULT_REPORT_TIME, DEFAULT_STAGE_REPORT_MIN_DAYS,
    INACTIVITY_REPORT_MIN_DAYS_PARAM, INACTIVITY_REPORT_MONTHDAY_PARAM, INACTIVITY_REPORT_PARAM,
    INACTIVITY_REPORT_PERIOD_PARAM, INACTIVITY_REPORT_TIME_PARAM, INACTIVITY_REPORT_WEEKDAY_PARAM,
    PIPELINE_REPORTS, REPORT_PERIOD_SELECTION, STAGE_REPORT_MIN_DAYS_PARAM,
    STAGE_REPORT_MONTHDAY_PARAM, STAGE_REPORT_PARAM, STAGE_REPORT_PERIOD_PARAM,
    STAGE_REPORT_TIME_PARAM, STAGE_REPORT_TZ_PARAM, STAGE_REPORT_WEEKDAY_PARAM,
)

WEEKDAY_SELECTION = [
    ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'),
    ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday'),
]


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Hierarchy ─────────────────────────────────────────────────
    # Leadership is picked here; managers are sales team leaders and BDAs
    # their team members, both taken from the sales teams (see crm_lead.py).
    crm_leadership_ids = fields.Many2many(
        related='company_id.crm_leadership_ids', readonly=False,
    )

    # ── Change notifications ──────────────────────────────────────
    crm_change_notify = fields.Boolean(
        string='Change Notifications',
        config_parameter='crm_consulting.change_notify',
        help="Email whenever an opportunity is created, deleted, or a change "
             "to it is recorded in its audit log - to everyone above whoever "
             "made the change, and never to them.",
    )

    # ── Stage Ageing Report ───────────────────────────────────────
    crm_stage_reminders = fields.Boolean(
        string='Stage Ageing Report',
        config_parameter=STAGE_REPORT_PARAM,
        help="On the schedule set below, email an Excel list of every active "
             "client whose opportunity has not progressed beyond its current "
             "stage for the days set below.",
    )
    crm_stage_report_period = fields.Selection(
        REPORT_PERIOD_SELECTION, string='Frequency', default=DEFAULT_REPORT_PERIOD,
        config_parameter=STAGE_REPORT_PERIOD_PARAM,
    )
    crm_stage_report_weekday = fields.Selection(
        WEEKDAY_SELECTION, string='On', default='0',
        config_parameter=STAGE_REPORT_WEEKDAY_PARAM,
    )
    crm_stage_report_monthday = fields.Integer(
        string='On day', default=DEFAULT_REPORT_MONTHDAY,
        config_parameter=STAGE_REPORT_MONTHDAY_PARAM,
        help="Day of the month, 1 to 31. In a month without that day, the "
             "report goes out on the month's last day.",
    )
    crm_stage_report_time = fields.Float(
        string='At', default=DEFAULT_REPORT_TIME,
        config_parameter=STAGE_REPORT_TIME_PARAM,
        help="Time of day the report goes out, in your own timezone.",
    )
    crm_stage_report_min_days = fields.Integer(
        string='Flag after', default=DEFAULT_STAGE_REPORT_MIN_DAYS,
        config_parameter=STAGE_REPORT_MIN_DAYS_PARAM,
        help="A client is listed once its opportunity has remained in the same "
             "stage for this many days or more, counted to the day the report "
             "goes out.",
    )
    crm_stage_reminder_recipient_ids = fields.Many2many(
        related='company_id.crm_stage_reminder_recipient_ids', readonly=False,
    )

    # ── Client Inactivity Report ──────────────────────────────────
    crm_inactivity_report = fields.Boolean(
        string='Client Inactivity Report',
        config_parameter=INACTIVITY_REPORT_PARAM,
        help="On the schedule set below, email an Excel list of every active "
             "client whose opportunity has had no recorded activity - no edit, "
             "chatter message or activity - for the days set below.",
    )
    crm_inactivity_report_period = fields.Selection(
        REPORT_PERIOD_SELECTION, string='Frequency', default=DEFAULT_REPORT_PERIOD,
        config_parameter=INACTIVITY_REPORT_PERIOD_PARAM,
    )
    crm_inactivity_report_weekday = fields.Selection(
        WEEKDAY_SELECTION, string='On', default='0',
        config_parameter=INACTIVITY_REPORT_WEEKDAY_PARAM,
    )
    crm_inactivity_report_monthday = fields.Integer(
        string='On day', default=DEFAULT_REPORT_MONTHDAY,
        config_parameter=INACTIVITY_REPORT_MONTHDAY_PARAM,
        help="Day of the month, 1 to 31. In a month without that day, the "
             "report goes out on the month's last day.",
    )
    crm_inactivity_report_time = fields.Float(
        string='At', default=DEFAULT_REPORT_TIME,
        config_parameter=INACTIVITY_REPORT_TIME_PARAM,
        help="Time of day the report goes out, in your own timezone.",
    )
    crm_inactivity_report_min_days = fields.Integer(
        string='Flag after', default=DEFAULT_INACTIVITY_REPORT_MIN_DAYS,
        config_parameter=INACTIVITY_REPORT_MIN_DAYS_PARAM,
        help="A client is listed once nobody has done anything on its "
             "opportunity for this many days or more, counted to the day the "
             "report goes out.",
    )
    crm_inactivity_report_recipient_ids = fields.Many2many(
        related='company_id.crm_inactivity_report_recipient_ids', readonly=False,
    )

    # ── Activity reminders ────────────────────────────────────────
    crm_activity_reminders = fields.Boolean(
        string='Activity Reminders',
        config_parameter='crm_consulting.activity_reminders',
        help="Email before a scheduled activity on an opportunity is due.",
    )
    crm_activity_reminder_day_ids = fields.Many2many(
        'crm.reminder.day', 'crm_settings_activity_reminder_day_rel',
        string='Send at',
    )
    crm_activity_reminder_type_ids = fields.Many2many(
        related='company_id.crm_activity_reminder_type_ids', readonly=False,
    )
    crm_activity_reminders_team_leader = fields.Boolean(
        string='Also remind their sales team leader',
        config_parameter='crm_consulting.activity_reminders_team_leader',
        help="The leader of the sales team the person assigned is in.",
    )
    crm_activity_reminders_leadership = fields.Boolean(
        string='Also remind leadership',
        config_parameter='crm_consulting.activity_reminders_leadership',
    )

    # ── Chatter mentions ──────────────────────────────────────────
    crm_mention_email = fields.Boolean(
        string='Email Tagged Colleagues',
        config_parameter='crm_consulting.mention_email',
        help="Email anyone tagged with @ in an opportunity's chatter, saying "
             "who tagged them on which opportunity, with the message and a "
             "button into it - whatever their own notification preference. "
             "The message stays in their Inbox too.",
    )

    # The recipient lists the Select everyone and Clear buttons may fill, each
    # a field of the company. The button names the list in its context.
    _CRM_RECIPIENT_FIELDS = (
        'crm_stage_reminder_recipient_ids',
        'crm_inactivity_report_recipient_ids',
    )

    _CRM_DAY_FIELDS = {
        'crm_activity_reminder_day_ids': ACTIVITY_REMINDER_DAYS_PARAM,
    }

    @api.model
    def get_values(self):
        values = super().get_values()
        # Any number in a parameter not yet offered as a chip - set from
        # developer mode, say - becomes one, so saving cannot drop it.
        Day = self.env['crm.reminder.day'].sudo()
        Lead = self.env['crm.lead']
        for fname, param in self._CRM_DAY_FIELDS.items():
            chips = Day.browse()
            for days in Lead._get_reminder_days(param):
                chips |= Day._get_or_create(days)
            values[fname] = [(6, 0, chips.ids)]
        return values

    def set_values(self):
        for prefix, title in (('crm_stage_report', _('Stage Ageing Report')),
                              ('crm_inactivity_report', _('Client Inactivity Report'))):
            if self[f'{prefix}_min_days'] < 1:
                raise ValidationError(_("%s: 'Flag after' has to be at least 1 day.", title))
            if self[f'{prefix}_period'] == 'monthly' \
                    and not 1 <= self[f'{prefix}_monthday'] <= 31:
                raise ValidationError(_("%s: the day of the month has to be from 1 to 31.",
                                        title))
            if not 0 <= self[f'{prefix}_time'] < 24:
                raise ValidationError(_("%s: the time has to be between 00:00 and 23:59.",
                                        title))
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        for fname, param in self._CRM_DAY_FIELDS.items():
            days = sorted(set(self[fname].mapped('days')), reverse=True)
            params.set_param(param, ','.join(map(str, days)))
        self._crm_schedule_pipeline_reports()

    # ── Pipeline report schedules ─────────────────────────────────
    # The settings field holding each report's time of day.
    _CRM_REPORT_TIME_FIELDS = {
        'stage': 'crm_stage_report_time',
        'inactivity': 'crm_inactivity_report_time',
    }

    @api.model
    def _crm_get_report_cron(self, kind):
        return self.sudo().with_context(active_test=False).env.ref(
            PIPELINE_REPORTS[kind]['cron'], raise_if_not_found=False)

    def _crm_schedule_pipeline_reports(self):
        """Run each report's job daily at its time of day, in the timezone of
        whoever is saving - and remember that timezone, so the reports read
        their weekday, day of the month and day counts in it too. The job
        itself sends only on the days the frequency names.

        A job already set to run then is left alone, so saving other settings
        never shifts it.
        """
        tz_name = self.env.user.tz or 'UTC'
        self.env['ir.config_parameter'].sudo().set_param(STAGE_REPORT_TZ_PARAM, tz_name)
        for kind, time_field in self._CRM_REPORT_TIME_FIELDS.items():
            cron = self._crm_get_report_cron(kind)
            if not cron:
                continue
            nextcall = self._crm_next_daily_call(self[time_field], tz_name, self.env.cr.now())
            if cron.nextcall != nextcall or cron.interval_type != 'days' \
                    or cron.interval_number != 1:
                cron.write({'nextcall': nextcall, 'interval_number': 1, 'interval_type': 'days'})

    @api.model
    def _crm_next_daily_call(self, hours, tz_name, now_utc):
        """The next time the clock in tz_name reads hours (9.5 is 09:30)
        after now_utc, as naive UTC."""
        tz = pytz.timezone(tz_name)
        local_now = pytz.utc.localize(now_utc).astimezone(tz)
        minutes = min(round((hours or 0) * 60), 24 * 60 - 1)
        at = time(minutes // 60, minutes % 60)
        target = tz.localize(datetime.combine(local_now.date(), at))
        if target <= local_now:
            target = tz.localize(datetime.combine(local_now.date() + timedelta(days=1), at))
        return target.astimezone(pytz.utc).replace(tzinfo=None)

    @api.model
    def _crm_next_report_call(self, weekday, tz_name, now_utc):
        """The next 00:00 on weekday in tz_name after now_utc, as naive UTC."""
        tz = pytz.timezone(tz_name)
        local_now = pytz.utc.localize(now_utc).astimezone(tz)
        day = local_now.date() + timedelta(days=(weekday - local_now.weekday()) % 7)
        target = tz.localize(datetime.combine(day, time.min))
        if target <= local_now:
            target = tz.localize(datetime.combine(day + timedelta(days=7), time.min))
        return target.astimezone(pytz.utc).replace(tzinfo=None)

    def action_crm_stage_report_send_now(self):
        """Send this week's Stage Ageing Report straight away, as of today -
        to check what it looks like, or to catch someone up."""
        return self._crm_send_report_now('stage', _('Stage Ageing Report'))

    def action_crm_inactivity_report_send_now(self):
        """Send this week's Client Inactivity Report straight away, as of today."""
        return self._crm_send_report_now('inactivity', _('Client Inactivity Report'))

    def _crm_send_report_now(self, kind, title):
        sent_to = self.env['crm.lead']._send_pipeline_report(kind)
        if not sent_to:
            raise UserError(_("Pick at least one person with an email address under "
                              "'Send to' first."))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('%(title)s sent to %(count)s %(who)s.', title=title, count=sent_to,
                             who=_('person') if sent_to == 1 else _('people')),
            },
        }

    # ── Select everyone / Clear ───────────────────────────────────
    def action_crm_recipients_select_all(self):
        """Put every internal user who can be emailed on the list."""
        self._crm_set_recipients(self.env['res.users'].search([
            ('share', '=', False), ('email', '!=', False)]))

    def action_crm_recipients_clear(self):
        """Take everyone off the list."""
        self._crm_set_recipients(self.env['res.users'])

    def _crm_set_recipients(self, users):
        fname = self.env.context.get('recipient_field')
        if fname not in self._CRM_RECIPIENT_FIELDS:
            raise UserError(_('Unknown recipient list: %s', fname))
        # Straight onto the company: the settings form saves before running
        # a button and reloads after, so the list shows the change at once.
        self.company_id[fname] = users
