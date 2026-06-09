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

    x_recruiter_ids = fields.Many2many(
        'res.users',
        'hr_job_recruiter_rel',
        'job_id', 'user_id',
        string='Recruiters',
        domain="[('share', '=', False)]",
    )

    @api.model_create_multi
    def create(self, vals_list):
        jobs = super().create(vals_list)
        for job in jobs:
            # Sync original user_id with first recruiter in x_recruiter_ids
            if job.x_recruiter_ids and not job.user_id:
                job.user_id = job.x_recruiter_ids[0]
            # If user_id was set directly and x_recruiter_ids is empty, sync back
            elif job.user_id and not job.x_recruiter_ids:
                job.x_recruiter_ids = [(4, job.user_id.id)]
        return jobs

    def write(self, vals):
        res = super().write(vals)
        if 'x_recruiter_ids' in vals:
            for job in self:
                if job.x_recruiter_ids:
                    # Update primary user_id if not among the selected recruiters
                    if job.user_id not in job.x_recruiter_ids:
                        job.user_id = job.x_recruiter_ids[0]
                else:
                    job.user_id = False
        elif 'user_id' in vals:
            for job in self:
                if job.user_id and job.user_id not in job.x_recruiter_ids:
                    job.x_recruiter_ids = [(4, job.user_id.id)]
        return res

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
