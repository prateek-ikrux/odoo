# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Users rather than typed addresses, so someone who leaves is simply
    # archived. Held here because a settings field cannot keep a many2many in
    # a system parameter. The opportunity's own BDAs are added on every send
    # and need not be picked.
    crm_change_recipient_ids = fields.Many2many(
        'res.users', 'crm_change_recipient_rel', 'company_id', 'user_id',
        string='CRM Change Notification Recipients',
        domain="[('share', '=', False)]",
    )
    crm_stage_reminder_recipient_ids = fields.Many2many(
        'res.users', 'crm_stage_reminder_recipient_rel', 'company_id', 'user_id',
        string='CRM Stuck-in-Stage Reminder Recipients',
        domain="[('share', '=', False)]",
    )
    crm_activity_reminder_recipient_ids = fields.Many2many(
        'res.users', 'crm_activity_reminder_recipient_rel', 'company_id', 'user_id',
        string='CRM Activity Reminder Recipients',
        domain="[('share', '=', False)]",
    )
    crm_activity_reminder_type_ids = fields.Many2many(
        'mail.activity.type', 'crm_activity_reminder_type_rel', 'company_id', 'type_id',
        string='CRM Activity Reminder Types',
        domain="['|', ('res_model', '=', False), ('res_model', '=', 'crm.lead')]",
        help="Only activities of these types send a reminder before they are due.",
    )
