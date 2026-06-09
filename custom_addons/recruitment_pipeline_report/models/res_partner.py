# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_client_department_id = fields.Many2one(
        'hr.department',
        string='Client',
        index=True,
        help='Client organization this contact belongs to (used for job POC selection).',
    )
