# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .crm_lead import ACTIVITY_REMINDER_DAYS_PARAM


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    # The days-before mark of the last reminder sent for this activity, so a
    # repeated run sends nothing new. Zero means none yet; moving the due date
    # resets it.
    crm_reminder_sent_days = fields.Integer(readonly=True, copy=False)

    def write(self, vals):
        if 'date_deadline' in vals:
            vals.setdefault('crm_reminder_sent_days', 0)
        return super().write(vals)

    @api.model
    def _cron_send_crm_activity_reminders(self):
        """Remind before activities on opportunities fall due. Runs nightly.

        A mark is reached once the activity is that many days away or fewer.
        The one sent is the most urgent mark reached, and only if it is more
        urgent than what already went out - so a repeated run is a no-op, and
        an activity scheduled for tomorrow gets the 1 day reminder rather than
        a 3 day one that no longer fits. Done activities are archived, so they
        drop out on their own.
        """
        Lead = self.env['crm.lead']
        if not Lead._notify_enabled('crm_consulting.activity_reminders'):
            return True
        days = Lead._get_reminder_days(ACTIVITY_REMINDER_DAYS_PARAM)
        company = self.env.company.sudo()
        types = company.crm_activity_reminder_type_ids
        if not days or not types:
            return True
        remind_team_leader = Lead._notify_enabled('crm_consulting.activity_reminders_team_leader')
        remind_leadership = Lead._notify_enabled('crm_consulting.activity_reminders_leadership')
        today = fields.Date.context_today(self)
        activities = self.search([
            ('res_model', '=', 'crm.lead'),
            ('activity_type_id', 'in', types.ids),
            ('date_deadline', '>=', today),
            ('date_deadline', '<=', fields.Date.add(today, days=max(days))),
        ])
        # One opportunity often has several activities due; look each up once.
        leads = {
            lead.id: lead
            for lead in Lead.browse(set(activities.mapped('res_id'))).exists()
            if lead.active and lead.type == 'opportunity'
        }
        for activity in activities:
            lead = leads.get(activity.res_id)
            if not lead:
                continue
            days_left = (activity.date_deadline - today).days
            reached = [d for d in days if days_left <= d]
            if not reached:
                continue
            mark = min(reached)
            if activity.crm_reminder_sent_days and mark >= activity.crm_reminder_sent_days:
                continue
            sent = lead._send_lead_mail(
                'crm_consulting_customization.mail_template_crm_activity_due',
                Lead._mail_partners(activity._get_crm_reminder_users(
                    lead, remind_team_leader, remind_leadership)),
                {'crm_activity': {
                    'type': activity.activity_type_id.name or '',
                    'icon': activity.activity_type_id.icon or '',
                    'summary': activity.summary or '',
                    'note': activity.note or '',
                    'days_left': days_left,
                    'accent': '#C0392B' if days_left <= 1 else '#D68910',
                    'due_on': Lead._long_date(self.env, activity.date_deadline),
                    'assigned_to': activity.user_id.name or '',
                    'scheduled_by': activity.create_uid.name or '',
                }},
            )
            if sent:
                activity.crm_reminder_sent_days = mark
        return True

    def _get_crm_reminder_users(self, lead, team_leader, leadership):
        """The assignee, and above them their sales team leader and
        leadership as the two settings ticks say.

        An activity assigned to nobody is the opportunity's BDAs' to do, so
        they stand in for the assignee.
        """
        self.ensure_one()
        Lead = self.env['crm.lead']
        assignees = self.user_id or lead._get_bda_users()
        users = assignees
        for assignee in assignees:
            users |= Lead._get_users_above(assignee, team_leader=team_leader, leadership=leadership)
        return users
