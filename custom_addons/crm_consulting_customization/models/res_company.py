# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Users rather than typed addresses, so someone who leaves is simply
    # archived. Held here because a settings field cannot keep a many2many in
    # a system parameter. Both lists start empty.
    #
    # Leadership is the top of the hierarchy change notifications and
    # activity reminders follow (see crm_lead.py); managers and BDAs below it
    # come from the sales teams, so they are not listed here.
    crm_leadership_ids = fields.Many2many(
        'res.users', 'crm_leadership_rel', 'company_id', 'user_id',
        string='CRM Leadership',
        domain="[('share', '=', False)]",
    )
    crm_stage_reminder_recipient_ids = fields.Many2many(
        'res.users', 'crm_stage_reminder_recipient_rel', 'company_id', 'user_id',
        string='CRM Stage Ageing Report Recipients',
        domain="[('share', '=', False)]",
    )
    crm_inactivity_report_recipient_ids = fields.Many2many(
        'res.users', 'crm_inactivity_report_recipient_rel', 'company_id', 'user_id',
        string='CRM Client Inactivity Report Recipients',
        domain="[('share', '=', False)]",
    )
    crm_activity_reminder_type_ids = fields.Many2many(
        'mail.activity.type', 'crm_activity_reminder_type_rel', 'company_id', 'type_id',
        string='CRM Activity Reminder Types',
        domain="['|', ('res_model', '=', False), ('res_model', '=', 'crm.lead')]",
        help="Only activities of these types send a reminder before they are due.",
    )
