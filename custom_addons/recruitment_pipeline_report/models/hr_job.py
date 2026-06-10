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

    # ── New fields ────────────────────────────────────────────────
    x_rec_id = fields.Char(
        string='Rec ID',
        copy=False,
        help='Unique identifier for this job position.',
    )

    x_min_experience = fields.Integer(
        string='Min Experience (Yrs)',
        default=0,
    )

    x_max_experience = fields.Integer(
        string='Max Experience (Yrs)',
        default=0,
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

    x_budget = fields.Char(
        string='Bill Rate / Budget',
        help='For Consulting roles: the bill rate agreed with the client.\n'
             'For FTE roles: the approved budget for this position.\n'
             'Displayed as "N/A" in the Applicant Tracker for the other role type.',
    )

    # ── Create / write hooks ──────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        jobs = super().create(vals_list)
        for job in jobs:
            # Keep user_id in sync with recruiter list
            if job.x_recruiter_ids and not job.user_id:
                job.user_id = job.x_recruiter_ids[0]
            elif job.user_id and not job.x_recruiter_ids:
                job.x_recruiter_ids = [(4, job.user_id.id)]
        return jobs

    def write(self, vals):
        res = super().write(vals)
        if 'x_recruiter_ids' in vals:
            for job in self:
                if job.x_recruiter_ids:
                    if job.user_id not in job.x_recruiter_ids:
                        job.user_id = job.x_recruiter_ids[0]
                else:
                    job.user_id = False
        elif 'user_id' in vals:
            for job in self:
                if job.user_id and job.user_id not in job.x_recruiter_ids:
                    job.x_recruiter_ids = [(4, job.user_id.id)]
        return res

    # ── Display name computation ──────────────────────────────────

    def _job_display_label(self, rec_id, name, department, employment_type,
                           min_exp, max_exp):
        """
        Format: [JOB0001] Infosys - Python Developer | FTE | 2-4 Yrs
        """
        emp_labels = {'fte': 'FTE', 'consulting': 'Consulting'}
        prefix = f'[{rec_id}] ' if rec_id else ''
        client = department.display_name if department else ''
        role   = name or ''
        emp    = emp_labels.get(employment_type, '')
        if min_exp and not max_exp:
            exp = f'{min_exp}+ Yrs'
        elif min_exp or max_exp:
            exp = f'{min_exp}-{max_exp} Yrs'
        else:
            exp = ''

        core  = f'{client} - {role}' if client else role
        label = prefix + core
        if emp:
            label += f' | {emp}'
        if exp:
            label += f' | {exp}'
        return label

    @api.depends('name', 'department_id', 'x_employment_type',
                 'x_rec_id', 'x_min_experience', 'x_max_experience')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec._job_display_label(
                rec.x_rec_id, rec.name, rec.department_id,
                rec.x_employment_type, rec.x_min_experience, rec.x_max_experience,
            )

    @api.depends('name', 'department_id', 'x_employment_type',
                 'x_rec_id', 'x_min_experience', 'x_max_experience')
    def _compute_display_name_with_type(self):
        for rec in self:
            rec.x_display_name = rec._job_display_label(
                rec.x_rec_id, rec.name, rec.department_id,
                rec.x_employment_type, rec.x_min_experience, rec.x_max_experience,
            )
