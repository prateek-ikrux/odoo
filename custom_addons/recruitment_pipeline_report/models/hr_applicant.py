# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # ── Readonly mirrors from job position ────────────────────────
    x_job_location_ids = fields.Many2many(
        related='job_id.x_location_ids',
        string='Job Available Locations',
        readonly=True,
    )

    x_role_status = fields.Selection(
        related='job_id.x_role_status',
        string='Role Status',
        store=True,
        readonly=True,
    )

    x_sub_status = fields.Selection(
        related='job_id.x_sub_status',
        string='Role Status Remarks',
        store=True,
        readonly=True,
    )

    x_employment_type = fields.Selection(
        related='job_id.x_employment_type',
        string='Employment Type',
        store=True,
        readonly=True,
    )

    x_poc_id = fields.Many2one(
        related='job_id.x_poc_id',
        string='POC',
        store=True,
        readonly=True,
    )

    x_no_of_positions = fields.Integer(
        related='job_id.no_of_recruitment',
        string='No. of Positions',
        store=True,
        readonly=True,
    )

    x_req_id = fields.Char(
        related='job_id.x_req_id',
        string='Req ID',
        store=True,
        readonly=True,
    )

    # Deprecated alias — see note in hr_job.py
    x_rec_id = fields.Char(
        related='job_id.x_req_id',
        string='Req ID (deprecated)',
        store=False,
        readonly=True,
    )

    x_min_experience = fields.Integer(
        related='job_id.x_min_experience',
        string='Min Experience (Yrs)',
        store=True,
        readonly=True,
    )

    x_max_experience = fields.Integer(
        related='job_id.x_max_experience',
        string='Max Experience (Yrs)',
        store=True,
        readonly=True,
    )

    # ── Last Working Day ─────────────────────────────────────────
    x_lwd = fields.Date(
        string='Last Working Date',
        help='Last working day of the candidate.',
    )

    # ── Candidate Details ─────────────────────────────────────────
    # Candidate Number = partner_phone (native hr.applicant field)

    x_skill_ids = fields.Many2many(
        'recruitment.skill',
        'hr_applicant_skill_rel',
        'applicant_id', 'skill_id',
        string='Skill',
        help='Candidate Skills selected from the shared skill master.'
    )

    x_total_experience = fields.Char(
        string='Total Experience',
        help='Total years of professional experience (e.g. "5.5 Yrs").',
    )

    x_relevant_experience = fields.Char(
        string='Relevant Experience',
        help='Years of experience relevant to the applied role.',
    )

    x_current_organization = fields.Char(
        string='Current Organization',
        help='Name of the candidate\'s current employer.',
    )

    x_designation = fields.Char(
        string='Designation',
        help='Current job title / designation of the candidate.',
    )

    x_education = fields.Char(
        string='Education',
        help='Highest educational qualification of the candidate.',
    )

    # ── Location & Availability ───────────────────────────────────
    x_current_location_id = fields.Many2one(
        'recruitment.city',
        string='Current Location',
        help='City where the candidate currently resides.',
    )

    x_preferred_location_ids = fields.Many2many(
        'recruitment.city',
        'hr_applicant_preferred_city_rel',
        'applicant_id', 'city_id',
        string='Preferred Location',
        help='Cities the candidate prefers to work in. Should be filtered by available job locations.',
    )

    x_open_to_anywhere = fields.Boolean(
        string='Open to Anywhere',
        default=False,
        help='Indicates if the candidate is open to relocating anywhere.',
    )

    x_notice_period = fields.Selection(
        selection=[
            ('30_days',           '30 Days'),
            ('60_days',           '60 Days'),
            ('90_days',           '90 Days'),
            ('immediate_joiner',  'Immediate Joiner'),
        ],
        string='Notice Period',
        help='Notice period of the candidate.',
    )

    # ── Compensation ──────────────────────────────────────────────
    x_current_ctc_lpa = fields.Float(
        string='Current CTC (LPA)',
    )

    x_expected_ctc_lpa = fields.Float(
        string='Expected CTC (LPA)',
    )

    x_offer_in_hand_ids = fields.Many2many(
        'hr.applicant.offer.tag',
        string='Offer in Hand (LPA)',
        help='Any competing offers the candidate currently holds (multiple values allowed).',
    )

    x_budget_lpa_display = fields.Float(
        string='Budget (LPA)',
        compute='_compute_budget_bill_rate_display_new',
        store=True,
    )

    x_bill_rate_lpm_display = fields.Float(
        string='Bill Rate (LPM)',
        compute='_compute_budget_bill_rate_display_new',
        store=True,
    )

    @api.depends('job_id.x_budget_lpa', 'job_id.x_bill_rate_lpm', 'job_id.x_employment_type')
    def _compute_budget_bill_rate_display_new(self):
        for rec in self:
            emp_type = rec.job_id.x_employment_type
            if emp_type == 'fte':
                rec.x_budget_lpa_display = rec.job_id.x_budget_lpa
                rec.x_bill_rate_lpm_display = 0.0
            elif emp_type == 'consulting':
                rec.x_budget_lpa_display = 0.0
                rec.x_bill_rate_lpm_display = rec.job_id.x_bill_rate_lpm
            else:
                rec.x_budget_lpa_display = 0.0
                rec.x_bill_rate_lpm_display = 0.0

    # ── Assessment fields ─────────────────────────────────────────
    x_assessment_link_received = fields.Selection(
        selection=[('yes', 'Yes'), ('no', 'No')],
        string='Assessment Link Received',
        default='no',
    )

    x_assessment_taken = fields.Selection(
        selection=[('yes', 'Yes'), ('no', 'No')],
        string='Assessment Taken',
        default='no',
    )

    x_assessment_feedback = fields.Selection(
        selection=[('select', 'Select'), ('reject', 'Reject')],
        string='Assessment Feedback',
    )

    # ── Application Details ───────────────────────────────────────
    x_client_portal_status = fields.Selection(
        selection=[
            ('uploaded',     'Uploaded'),
            ('not_uploaded', 'Not Uploaded'),
        ],
        string='Client Portal Status',
        default='not_uploaded',
        help='Indicates whether the candidate profile has been uploaded to the client portal.',
    )

    # ── Additional Information ────────────────────────────────────
    x_reason_for_job_change = fields.Text(
        string='Reason for Job Change',
        help='Candidate\'s stated reason for looking for a new opportunity.',
    )

    x_remarks = fields.Text(
        string='Remarks',
        help='Internal recruiter remarks / notes about the candidate.',
    )

    # ── Custom Date Display (Ordinal format like 2nd May 2026) ────
    x_create_date_display = fields.Char(
        string='Application Date',
        compute='_compute_date_displays',
    )

    x_lwd_display = fields.Char(
        string='Last Working Date',
        compute='_compute_date_displays',
    )

    @api.depends('create_date', 'x_lwd')
    def _compute_date_displays(self):
        def format_ordinal_date(d):
            if not d: return ''
            day = d.day
            if 4 <= day <= 20 or 24 <= day <= 30:
                suf = "th"
            else:
                suf = ["st", "nd", "rd"][day % 10 - 1]
            return d.strftime(f"{day}{suf} %B %Y")

        for rec in self:
            rec.x_create_date_display = format_ordinal_date(rec.create_date)
            rec.x_lwd_display = format_ordinal_date(rec.x_lwd)

    # ── Constraint: hard block saving an invalid recruiter ────────
    @api.constrains('user_id', 'job_id')
    def _check_recruiter_belongs_to_job(self):
        for rec in self:
            if not rec.user_id or not rec.job_id:
                continue
            allowed = rec.job_id.x_recruiter_ids
            if rec.user_id not in allowed:
                allowed_names = ', '.join(allowed.mapped('name')) or 'none assigned'
                raise ValidationError(
                    f'Recruiter "{rec.user_id.name}" is not assigned to the job '
                    f'position "{rec.job_id.name}".\n'
                    f'Allowed recruiters: {allowed_names}.'
                )

    # ── Onchange: enforce domain + clear invalid recruiter on job change ──
    @api.onchange('job_id')
    def _onchange_job_id_recruiter(self):
        recruiter_ids = self.job_id.x_recruiter_ids.ids if self.job_id else []

        if self.user_id and self.user_id.id not in recruiter_ids:
            self.user_id = False

        if not self.user_id and recruiter_ids:
            self.user_id = recruiter_ids[0]

        return {
            'domain': {
                'user_id': [('id', 'in', recruiter_ids)],
            }
        }

    # ── Onchange: validate recruiter immediately when changed directly ──
    @api.onchange('user_id')
    def _onchange_recruiter_id_validate(self):
        if not self.user_id or not self.job_id:
            return
        recruiter_ids = self.job_id.x_recruiter_ids.ids
        if self.user_id.id not in recruiter_ids:
            allowed_names = ', '.join(self.job_id.x_recruiter_ids.mapped('name')) or 'none assigned'
            self.user_id = False
            return {
                'warning': {
                    'title': 'Invalid Recruiter',
                    'message': (
                        f'The selected recruiter is not assigned to the job position '
                        f'"{self.job_id.name}".\n'
                        f'Allowed recruiters: {allowed_names}.'
                    ),
                }
            }

    # ── Export wizard openers (called from list view header buttons) ──────
    def action_open_tracker_export_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Applicant Tracker',
            'res_model': 'recruitment.applicant.tracker.wizard',
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
        }

    def action_open_assessment_export_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Internal Assessment Report',
            'res_model': 'recruitment.assessment.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
        }
