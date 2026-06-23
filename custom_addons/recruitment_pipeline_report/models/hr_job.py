# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
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
        string='Role Status Remarks',
    )

    # ── New fields ────────────────────────────────────────────────
    x_req_id_available = fields.Selection(
        selection=[('yes', 'Yes'), ('no', 'No')],
        string='Req ID Available?',
        default='yes',
        help='Select "Yes" if you already have a Requisition ID to enter manually. '
             'Select "No" to have one generated automatically when the job position is saved '
             '(format: REQ-2026-00001).',
    )

    x_req_id = fields.Char(
        string='Req ID',
        copy=False,
        help='Requisition ID for this job position. Enter manually (e.g. REQ-2024-001) '
             'if available, or set "Req ID Available?" to "No" to auto-generate one on save.',
    )

    _sql_constraints = [
        ('x_req_id_uniq', 'unique (x_req_id)', 'Req ID must be unique! This Req ID is already assigned to another job position.'),
    ]

    # Deprecated alias — kept only so existing ir.ui.view records that still
    # reference x_rec_id pass ORM validation during the upgrade. Odoo will
    # overwrite those view records with the new XML (using x_req_id) as part
    # of this same upgrade. Safe to remove in a future version.
    x_rec_id = fields.Char(
        related='x_req_id',
        string='Req ID (deprecated)',
        store=False,
        readonly=True,
    )

    x_min_experience = fields.Integer(
        string='Min Experience (Yrs)',
        default=0,
    )

    x_max_experience = fields.Integer(
        string='Max Experience (Yrs)',
        default=0,
    )

    @api.constrains('x_min_experience', 'x_max_experience')
    def _check_experience_range(self):
        for rec in self:
            if rec.x_min_experience < 0:
                raise ValidationError('Min Experience (Yrs) cannot be negative.')
            if rec.x_max_experience < 0:
                raise ValidationError('Max Experience (Yrs) cannot be negative.')
            # Max = 0 is treated as "not specified" (the field's default),
            # so it's skipped here rather than flagged as Min > Max.
            if rec.x_max_experience and rec.x_min_experience > rec.x_max_experience:
                raise ValidationError(
                    'Min Experience (Yrs) cannot be greater than Max Experience (Yrs).'
                )

    x_location_ids = fields.Many2many(
        'recruitment.city',
        'hr_job_city_rel',
        'job_id', 'city_id',
        string='Job Locations'
    )

    x_skill_ids = fields.Many2many(
        'recruitment.skill',
        'hr_job_skill_rel',
        'job_id', 'skill_id',
        string='Required Skills'
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



    x_budget_lpa = fields.Float(
        string='Budget (LPA)',
        help='Approved budget for FTE roles in Lakhs Per Annum.'
    )

    x_bill_rate_lpm = fields.Float(
        string='Bill Rate (LPM)',
        help='Agreed bill rate for Consulting roles in Lakhs Per Month.'
    )

    # @api.constrains('x_budget_lpa', 'x_bill_rate_lpm')
    # def _check_budget_bill_rate_not_negative(self):
    #     for rec in self:
    #         if rec.x_budget_lpa < 0:
    #             raise ValidationError('Budget (LPA) cannot be negative.')
    #         if rec.x_bill_rate_lpm < 0:
    #             raise ValidationError('Bill Rate (LPM) cannot be negative.')

    @api.constrains('x_budget_lpa', 'x_bill_rate_lpm', 'x_employment_type')
    def _check_budget_bill_rate_positive(self):
        for rec in self:
            if rec.x_employment_type == 'fte' and rec.x_budget_lpa <= 0:
                raise ValidationError('Budget (LPA) must be greater than zero for FTE roles.')
            if rec.x_employment_type == 'consulting' and rec.x_bill_rate_lpm <= 0:
                raise ValidationError('Bill Rate (LPM) must be greater than zero for Consulting roles.')

    # ── Create / write hooks ──────────────────────────────────────

    def _generate_unique_req_id(self):
        """Generate a unique Req ID using the ir.sequence, in the format
        REQ-2026-00001. Retries on the rare chance the sequence-issued
        number is already in use (defense-in-depth on top of the
        x_req_id_uniq SQL constraint), so every generated value is
        guaranteed unique."""
        Sequence = self.env['ir.sequence']
        for _attempt in range(100):
            candidate = Sequence.next_by_code('hr.job.x_req_id')
            if not candidate:
                raise ValidationError(
                    'Could not generate a Req ID automatically: the '
                    '"Job Req ID" sequence is missing. Please contact your administrator.'
                )
            if not self.env['hr.job'].sudo().search_count([('x_req_id', '=', candidate)]):
                return candidate
        raise ValidationError('Could not generate a unique Req ID. Please try again.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('x_req_id_available') == 'no' and not vals.get('x_req_id'):
                vals['x_req_id'] = self._generate_unique_req_id()
        jobs = super().create(vals_list)
        for job in jobs:
            # Keep user_id in sync with recruiter list
            if job.x_recruiter_ids and not job.user_id:
                job.user_id = job.x_recruiter_ids[0]
            elif job.user_id and not job.x_recruiter_ids:
                job.x_recruiter_ids = [(4, job.user_id.id)]
        return jobs

    def write(self, vals):
        # Auto-generate Req ID per-record when "Req ID Available?" is set to
        # "No" and no Req ID was explicitly supplied in this write. Handled
        # record-by-record so each job that needs one gets its own unique
        # value (relevant when writing on multiple jobs at once).
        wants_auto_req_id = vals.get('x_req_id_available') == 'no' and not vals.get('x_req_id')
        if wants_auto_req_id:
            for job in self:
                job_vals = vals
                if not job.x_req_id:
                    job_vals = dict(vals, x_req_id=self._generate_unique_req_id())
                super(HrJob, job).write(job_vals)
            res = True
        else:
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

    def _job_display_label(self, req_id, name, department, employment_type,
                           min_exp, max_exp):
        """
        Format: [JOB0001] Infosys - Python Developer | FTE | 2-4 Yrs
        """
        emp_labels = {'fte': 'FTE', 'consulting': 'Consulting'}
        prefix = f'[{req_id}] ' if req_id else ''
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
                 'x_req_id', 'x_min_experience', 'x_max_experience')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec._job_display_label(
                rec.x_req_id, rec.name, rec.department_id,
                rec.x_employment_type, rec.x_min_experience, rec.x_max_experience,
            )

    @api.depends('name', 'department_id', 'x_employment_type',
                 'x_req_id', 'x_min_experience', 'x_max_experience')
    def _compute_display_name_with_type(self):
        for rec in self:
            rec.x_display_name = rec._job_display_label(
                rec.x_req_id, rec.name, rec.department_id,
                rec.x_employment_type, rec.x_min_experience, rec.x_max_experience,
            )

    def create_action(self):
        """After creating a Job Position, redirect to its config/form page
        instead of the default applicant-stage kanban view."""
        self.ensure_one()
        form_view_id = self.env.ref('hr.view_hr_job_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': self.display_name or self.name,
            'res_model': 'hr.job',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(form_view_id, 'form')],
            'target': 'current',
        }
