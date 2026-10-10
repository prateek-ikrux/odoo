# -*- coding: utf-8 -*-
from odoo import api, fields, models

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
