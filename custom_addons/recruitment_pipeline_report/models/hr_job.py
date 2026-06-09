# -*- coding: utf-8 -*-
from odoo import models, fields, api
from .pipeline_constants import ROLE_STATUS_SELECTION, SUB_STATUS_SELECTION


class HrJob(models.Model):
    _inherit = 'hr.job'

    department_id = fields.Many2one(string='Client')

    x_employment_type = fields.Selection(
        selection=[
            ('fte',        'FTE'),
            ('consulting', 'Consulting'),
        ],
        string='Employment Type',
        default='fte',
    )

    x_poc_id = fields.Many2one(
        'res.partner',
        string='Point of Contact (POC)',
        domain="[('x_client_department_id', '=', department_id)]",
        help='External client contact who handles this job position.',
    )

    x_role_status = fields.Selection(
        selection=ROLE_STATUS_SELECTION,
        string='Role Status',
        default='active',
    )

    x_sub_status = fields.Selection(
        selection=SUB_STATUS_SELECTION,
        string='Sub Status',
    )

    x_display_name = fields.Char(
        string='Job Position',
        compute='_compute_display_name_with_type',
        store=True,
    )

    def _job_display_label(self, name, department, employment_type):
        """Build a disambiguated label: Role (Client - FTE)."""
        emp_labels = {'fte': 'FTE', 'consulting': 'Consulting'}
        parts = []
        if department:
            parts.append(department.display_name)
        emp = emp_labels.get(employment_type)
        if emp:
            parts.append(emp)
        if parts:
            return f"{name or ''} ({' - '.join(parts)})"
        return name or ''

    @api.depends('name', 'department_id', 'x_employment_type')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec._job_display_label(
                rec.name, rec.department_id, rec.x_employment_type,
            )

    @api.depends('name', 'department_id', 'x_employment_type')
    def _compute_display_name_with_type(self):
        for rec in self:
            rec.x_display_name = rec._job_display_label(
                rec.name, rec.department_id, rec.x_employment_type,
            )
