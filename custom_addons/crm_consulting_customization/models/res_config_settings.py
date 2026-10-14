# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .crm_lead import ACTIVITY_REMINDER_DAYS_PARAM, STAGE_REMINDER_DAYS_PARAM


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

    # ── Stuck-in-stage reminders ──────────────────────────────────
    crm_stage_reminders = fields.Boolean(
        string='Stuck-in-Stage Reminders',
        config_parameter='crm_consulting.stage_reminders',
        help="Email when an active client's opportunity stays in the same "
             "stage for the days picked below.",
    )
    # Shown as chips, but saved to a system parameter the cron reads;
    # get_values and set_values translate.
    crm_stage_reminder_day_ids = fields.Many2many(
        'crm.reminder.day', 'crm_settings_stage_reminder_day_rel',
        string='Send after',
    )
    crm_stage_reminder_recipient_ids = fields.Many2many(
        related='company_id.crm_stage_reminder_recipient_ids', readonly=False,
    )
    crm_stage_reminders_bda = fields.Boolean(
        string="Also send to the opportunity's BDAs",
        config_parameter='crm_consulting.stage_reminders_bda',
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

    # The recipient lists the Select everyone and Clear buttons may fill, each
    # a field of the company. The button names the list in its context.
    _CRM_RECIPIENT_FIELDS = (
        'crm_change_recipient_ids',
        'crm_stage_reminder_recipient_ids',
        'crm_activity_reminder_recipient_ids',
    )

    _CRM_DAY_FIELDS = {
        'crm_stage_reminder_day_ids': STAGE_REMINDER_DAYS_PARAM,
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
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        for fname, param in self._CRM_DAY_FIELDS.items():
            days = sorted(set(self[fname].mapped('days')), reverse=True)
            params.set_param(param, ','.join(map(str, days)))

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
