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
                Lead._mail_partners(
                    company.crm_activity_reminder_recipient_ids
                    | lead._get_bda_users() | activity.user_id),
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
