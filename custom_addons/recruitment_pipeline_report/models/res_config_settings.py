# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .notify_mixin import STUCK_REMINDER_DAYS_PARAM


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Client notifications ──────────────────────────────────────
    x_rp_client_notify = fields.Boolean(
        string='Client Notifications', config_parameter='recruitment_pipeline.client_notify')
    x_rp_client_notify_creator = fields.Boolean(
        string='Send to the person who created the client',
        config_parameter='recruitment_pipeline.client_notify_creator')
    x_rp_client_notify_assigned = fields.Boolean(
        string="Send to the client's Manager",
        config_parameter='recruitment_pipeline.client_notify_assigned')
    x_rp_client_recipient_ids = fields.Many2many(
        related='company_id.x_rp_client_recipient_ids', readonly=False)

    # ── Role notifications ────────────────────────────────────────
    x_rp_role_notify = fields.Boolean(
        string='Role Notifications', config_parameter='recruitment_pipeline.role_notify')
    x_rp_role_notify_creator = fields.Boolean(
        string='Send to the person who created the role',
        config_parameter='recruitment_pipeline.role_notify_creator')
    x_rp_role_notify_assigned = fields.Boolean(
        string='Send to the Recruitment Manager and Recruiters',
        config_parameter='recruitment_pipeline.role_notify_assigned')
    x_rp_role_recipient_ids = fields.Many2many(
        related='company_id.x_rp_role_recipient_ids', readonly=False)

    # ── Stuck-candidate reminders ─────────────────────────────────
    x_rp_stuck_notify = fields.Boolean(
        string='Stuck-Candidate Reminders', config_parameter='recruitment_pipeline.stuck_notify')
    x_rp_stuck_notify_creator = fields.Boolean(
        string='Send to the person who added the candidate',
        config_parameter='recruitment_pipeline.stuck_notify_creator')
    x_rp_stuck_notify_assigned = fields.Boolean(
        string="Send to the candidate's Recruiter and the Recruitment Manager",
        config_parameter='recruitment_pipeline.stuck_notify_assigned')
    # Shown as chips, but saved to the system parameter the cron reads;
    # get_values and set_values translate.
    x_rp_stuck_day_ids = fields.Many2many(
        'recruitment.reminder.day', 'rp_settings_stuck_day_rel', string='Send after')
    x_rp_stuck_recipient_ids = fields.Many2many(
        related='company_id.x_rp_stuck_recipient_ids', readonly=False)

    @api.model
    def get_values(self):
        values = super().get_values()
        # Any number in the parameter not yet offered as a chip - set from
        # developer mode, say - becomes one, so saving cannot drop it.
        Day = self.env['recruitment.reminder.day'].sudo()
        chips = Day.browse()
        for days in self.env['hr.applicant']._get_stuck_reminder_days():
            chips |= Day._get_or_create(days)
        values['x_rp_stuck_day_ids'] = [(6, 0, chips.ids)]
        return values

    def set_values(self):
        super().set_values()
        days = sorted(set(self.x_rp_stuck_day_ids.mapped('days')), reverse=True)
        self.env['ir.config_parameter'].sudo().set_param(
            STUCK_REMINDER_DAYS_PARAM, ','.join(map(str, days)))
