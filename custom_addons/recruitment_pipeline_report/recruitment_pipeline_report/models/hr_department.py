# -*- coding: utf-8 -*-
from odoo import models, fields


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    x_poc_contact_count = fields.Integer(
        string='POC Contacts',
        compute='_compute_poc_contact_count',
    )

    def _compute_poc_contact_count(self):
        partner_model = self.env['res.partner']
        for dept in self:
            dept.x_poc_contact_count = partner_model.search_count([
                ('x_client_department_id', '=', dept.id),
            ])

    def action_view_poc_contacts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'POC Contacts',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('x_client_department_id', '=', self.id)],
            'context': {
                'default_x_client_department_id': self.id,
                'search_default_x_client_department_id': self.id,
            },
        }
