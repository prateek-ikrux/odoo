# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .crm_lead import (
    ACTIVITY_REMINDER_DAYS_PARAM, DEFAULT_STAGE_REPORT_MIN_DAYS, STAGE_REPORT_MIN_DAYS_PARAM,
    STAGE_REPORT_PARAM, STAGE_REPORT_TZ_PARAM, STAGE_REPORT_WEEKDAY_PARAM,
)

WEEKDAY_SELECTION = [
    ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'),
    ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday'),
]


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Change notifications ──────────────────────────────────────
    crm_change_notify = fields.Boolean(
        string='Change Notifications',
        config_parameter='crm_consulting.change_notify',
        help="Email whenever an opportunity is created, deleted, or a change "
             "to it is recorded in its audit log.",
    )
    crm_change_recipient_ids = fields.Many2many(
        related='company_id.crm_change_recipient_ids', readonly=False,
    )
    crm_change_notify_bda = fields.Boolean(
        string="Also send to the opportunity's BDAs",
        config_parameter='crm_consulting.change_notify_bda',
    )

    # ── Stuck-in-stage report ─────────────────────────────────────
    crm_stage_reminders = fields.Boolean(
        string='Stuck-in-Stage Report',
        config_parameter=STAGE_REPORT_PARAM,
        help="Once a week, email an Excel list of every active client whose "
             "opportunity has not moved stage for the days set below.",
    )
    crm_stage_report_weekday = fields.Selection(
        WEEKDAY_SELECTION, string='Send every', default='0',
        config_parameter=STAGE_REPORT_WEEKDAY_PARAM,
        help="The report goes out at midnight at the start of this day, in "
             "your own timezone.",
    )
    crm_stage_report_min_days = fields.Integer(
        string='Stuck after', default=DEFAULT_STAGE_REPORT_MIN_DAYS,
        config_parameter=STAGE_REPORT_MIN_DAYS_PARAM,
        help="A client is listed once its opportunity has been in the same "
             "stage for this many days or more, counted to the day the report "
             "goes out.",
    )
    crm_stage_reminder_recipient_ids = fields.Many2many(
        related='company_id.crm_stage_reminder_recipient_ids', readonly=False,
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
    crm_activity_reminder_recipient_ids = fields.Many2many(
        related='company_id.crm_activity_reminder_recipient_ids', readonly=False,
    )
    crm_activity_reminders_bda = fields.Boolean(
        string="Also send to the opportunity's BDAs",
        config_parameter='crm_consulting.activity_reminders_bda',
    )
    crm_activity_reminders_assignee = fields.Boolean(
        string='Also send to the person the activity is assigned to',
        config_parameter='crm_consulting.activity_reminders_assignee',
    )

    # ── Chatter mentions ──────────────────────────────────────────
    crm_mention_email = fields.Boolean(
        string='Email Tagged Colleagues',
        config_parameter='crm_consulting.mention_email',
        help="Email anyone tagged with @ in an opportunity's chatter, even if "
             "they handle notifications in Odoo. The message stays in their "
             "Inbox too.",
    )

    # The recipient lists the Select everyone and Clear buttons may fill, each
    # a field of the company. The button names the list in its context.
    _CRM_RECIPIENT_FIELDS = (
        'crm_change_recipient_ids',
        'crm_stage_reminder_recipient_ids',
        'crm_activity_reminder_recipient_ids',
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
        if self.crm_stage_reminders and self.crm_stage_report_min_days < 1:
            raise ValidationError(_("'Stuck after' has to be at least 1 day."))
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        for fname, param in self._CRM_DAY_FIELDS.items():
            days = sorted(set(self[fname].mapped('days')), reverse=True)
            params.set_param(param, ','.join(map(str, days)))
        self._crm_schedule_stage_report()

    # ── Stuck-in-stage report schedule ────────────────────────────
    @api.model
    def _crm_get_stage_report_cron(self):
        return self.sudo().with_context(active_test=False).env.ref(
            'crm_consulting_customization.ir_cron_crm_stage_reminders',
            raise_if_not_found=False)

    def _crm_schedule_stage_report(self):
        """Point the weekly job at the next midnight that starts the picked
        weekday, in the timezone of whoever is saving - and remember that
        timezone, so the report counts days in it too.

        Left alone when it already points there, so saving other settings
        never shifts it.
        """
        cron = self._crm_get_stage_report_cron()
        if not cron:
            return
        tz_name = self.env.user.tz or 'UTC'
        self.env['ir.config_parameter'].sudo().set_param(STAGE_REPORT_TZ_PARAM, tz_name)
        nextcall = self._crm_next_report_call(int(self.crm_stage_report_weekday or 0), tz_name,
                                              self.env.cr.now())
        if cron.nextcall != nextcall or cron.interval_type != 'weeks' or cron.interval_number != 1:
            cron.write({'nextcall': nextcall, 'interval_number': 1, 'interval_type': 'weeks'})

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
        """Send this week's report straight away, as of today - to check
        what it looks like, or to catch someone up."""
        sent_to = self.env['crm.lead']._send_stage_report()
        if not sent_to:
            raise UserError(_("Pick at least one person with an email address under "
                              "'Send to' first."))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Stuck-in-stage report sent to %(count)s %(who)s.', count=sent_to,
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
