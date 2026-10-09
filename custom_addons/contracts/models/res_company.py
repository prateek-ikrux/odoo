# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    contracts_reminder_recipient_ids = fields.Many2many(
        'res.users', 'contracts_reminder_recipient_rel', 'company_id', 'user_id',
        string='Expiry Reminder Recipients',
        domain="[('share', '=', False)]",
        help="Users emailed before a contract runs out.",
    )
    contracts_change_recipient_ids = fields.Many2many(
        'res.users', 'contracts_change_recipient_rel', 'company_id', 'user_id',
        string='Change Notification Recipients',
        domain="[('share', '=', False)]",
        help="Users emailed whenever a contract is created or a change is "
             "recorded in its audit log. Kept apart from the expiry reminder "
             "recipients.",
    )
