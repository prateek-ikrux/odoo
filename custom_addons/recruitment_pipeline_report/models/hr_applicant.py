# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # ── Readonly mirrors from job position ────────────────────────
    x_role_status = fields.Selection(
        related='job_id.x_role_status',
        string='Role Status',
        store=True,
        readonly=True,
    )

    x_sub_status = fields.Selection(
        related='job_id.x_sub_status',
        string='Sub Status',
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

    x_rec_id = fields.Char(
        related='job_id.x_rec_id',
        string='Rec ID',
        store=True,
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

    # ── Per-applicant recruiter (many2one) ────────────────────────
    x_recruiter_id = fields.Many2one(
        'res.users',
        string='Recruiter',
        help='The recruiter handling this applicant. '
             'Must be one of the recruiters assigned to the job position.',
    )

    # ── Candidate Details ─────────────────────────────────────────
    # Candidate Number = partner_phone (native hr.applicant field)

    x_skill = fields.Char(
        string='Skill',
        help='Primary skill set of the candidate.',
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
    x_current_location = fields.Char(
        string='Current Location',
        help='City/region where the candidate currently resides.',
    )

    x_preferred_location = fields.Char(
        string='Preferred Location',
        help='City/region the candidate prefers to work in.',
    )

    x_notice_period = fields.Char(
        string='Notice Period',
        help='Notice period of the candidate (e.g. "30 days", "Immediate").',
    )

    # ── Compensation ──────────────────────────────────────────────
    x_current_ctc = fields.Char(
        string='Current CTC',
        help='Current cost-to-company of the candidate.',
    )

    x_expected_ctc = fields.Char(
        string='Expected CTC',
        help='Expected cost-to-company requested by the candidate.',
    )

    x_offer_in_hand = fields.Char(
        string='Offer in Hand',
        help='Any competing offer the candidate currently holds.',
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

    # ── Constraint: hard block saving an invalid recruiter ────────
    @api.constrains('x_recruiter_id', 'job_id')
    def _check_recruiter_belongs_to_job(self):
        for rec in self:
            if not rec.x_recruiter_id or not rec.job_id:
                continue
            allowed = rec.job_id.x_recruiter_ids
            if rec.x_recruiter_id not in allowed:
                allowed_names = ', '.join(allowed.mapped('name')) or 'none assigned'
                raise ValidationError(
                    f'Recruiter "{rec.x_recruiter_id.name}" is not assigned to the job '
                    f'position "{rec.job_id.name}".\n'
                    f'Allowed recruiters: {allowed_names}.'
                )

    # ── Onchange: enforce domain + clear invalid recruiter on job change ──
    @api.onchange('job_id')
    def _onchange_job_id_recruiter(self):
        recruiter_ids = self.job_id.x_recruiter_ids.ids if self.job_id else []

        if self.x_recruiter_id and self.x_recruiter_id.id not in recruiter_ids:
            self.x_recruiter_id = False

        if not self.x_recruiter_id and recruiter_ids:
            self.x_recruiter_id = recruiter_ids[0]

        return {
            'domain': {
                'x_recruiter_id': [('id', 'in', recruiter_ids)],
            }
        }

    # ── Onchange: validate recruiter immediately when changed directly ──
    @api.onchange('x_recruiter_id')
    def _onchange_recruiter_id_validate(self):
        if not self.x_recruiter_id or not self.job_id:
            return
        recruiter_ids = self.job_id.x_recruiter_ids.ids
        if self.x_recruiter_id.id not in recruiter_ids:
            allowed_names = ', '.join(self.job_id.x_recruiter_ids.mapped('name')) or 'none assigned'
            self.x_recruiter_id = False
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
