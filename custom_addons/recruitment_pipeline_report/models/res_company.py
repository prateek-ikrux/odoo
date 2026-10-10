# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # The people picked by name for each kind of recruitment email, on top of
    # the creator and the assigned people. Users rather than typed addresses,
    # so someone who leaves is simply archived; held here because a settings
    # field cannot keep a many2many in a system parameter.
    x_rp_client_recipient_ids = fields.Many2many(
        'res.users', 'rp_client_recipient_rel', 'company_id', 'user_id',
        string='Client Notification Recipients', domain="[('share', '=', False)]",
    )
    x_rp_role_recipient_ids = fields.Many2many(
        'res.users', 'rp_role_recipient_rel', 'company_id', 'user_id',
        string='Role Notification Recipients', domain="[('share', '=', False)]",
    )
    x_rp_stuck_recipient_ids = fields.Many2many(
        'res.users', 'rp_stuck_recipient_rel', 'company_id', 'user_id',
        string='Stuck-Candidate Reminder Recipients', domain="[('share', '=', False)]",
    )
