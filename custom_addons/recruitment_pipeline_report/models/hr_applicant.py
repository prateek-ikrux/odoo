# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # ── 5-star evaluation (overrides native 0–3 priority) ────────
    # Odoo's widget="priority" renders one star per non-zero option.
    # Extending the selection to 0–5 gives exactly 5 clickable stars.
    priority = fields.Selection(
        selection=[
            ('0', 'Normal'),
            ('1', '1 Star'),
            ('2', '2 Stars'),
            ('3', '3 Stars'),
            ('4', '4 Stars'),
            ('5', '5 Stars'),
        ],
        string='Evaluation',
        default='0',
    )

    # ── Fixed Source value ────────────────────────────────────────
    # Source is always "iKrux Engineering" — the field is readonly in the
    # view, defaulted here, and re-applied in create/write below so it
    # can't be changed via API, import, or by removing the readonly
    # attribute client-side.
    def _get_fixed_source_id(self):
        source = self.env.ref('recruitment_pipeline_report.utm_source_ikrux_engineering', raise_if_not_found=False)
        return source.id if source else False

    source_id = fields.Many2one(default=lambda self: self._get_fixed_source_id())

    @api.model_create_multi
    def create(self, vals_list):
        fixed_source_id = self._get_fixed_source_id()
        for vals in vals_list:
            if fixed_source_id:
                vals['source_id'] = fixed_source_id
            # Keep Client (department_id) in sync with the Job Position even
            # when job_id is set outside the applicant form (e.g. moving a
            # candidate from a Talent Pool onto a job), where the form's
            # onchange never runs.
            if vals.get('job_id') and not vals.get('department_id'):
                job = self.env['hr.job'].browse(vals['job_id'])
                vals['department_id'] = job.department_id.id
        records = super().create(vals_list)
        return records

    def write(self, vals):
        if 'source_id' in vals:
            fixed_source_id = self._get_fixed_source_id()
            if fixed_source_id:
                vals = dict(vals, source_id=fixed_source_id)
        if vals.get('job_id') and 'department_id' not in vals:
            job = self.env['hr.job'].browse(vals['job_id'])
            vals = dict(vals, department_id=job.department_id.id)
        res = super().write(vals)
        return res

    # ── Onchange: keep Client (department_id) synced with Job Position ────
    @api.onchange('job_id')
    def _onchange_job_id_department(self):
        if self.job_id:
            self.department_id = self.job_id.department_id

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

    @api.constrains('x_lwd', 'x_notice_period')
    def _check_lwd_not_past_for_serving_notice(self):
        """Only checked for 'Serving Notice Period': that date is a future
        commitment, so it shouldn't be in the past. 'Immediate Joiner' is
        exempt — that candidate may have already left their last job, so
        a past or today's date is legitimate there."""
        for rec in self:
            if rec.x_notice_period == 'serving_notice' and rec.x_lwd and rec.x_lwd < fields.Date.context_today(rec):
                raise ValidationError(
                    'Last Working Date cannot be in the past for a candidate Serving Notice Period.'
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

    x_total_experience = fields.Float(
        string='Total Experience (Yrs)',
        help='Total years of professional experience (e.g. 5.5).',
    )

    x_relevant_experience = fields.Float(
        string='Relevant Experience (Yrs)',
        help='Years of experience relevant to the applied role (e.g. 3.5).',
    )

    @api.constrains('x_total_experience', 'x_relevant_experience')
    def _check_experience_values(self):
        # Enforced as "> 0" rather than ">= 0" for the same reason as the
        # CTC fields below: required="1" on a Float widget doesn't stop a
        # user from saving with the pre-filled 0.0 left untouched, so
        # rejecting 0 here is what actually makes the field mandatory.
        for rec in self:
            if rec.x_total_experience < 0:
                raise ValidationError('Total Experience (Yrs) cannot be negative.')
            if rec.x_relevant_experience < 0:
                raise ValidationError('Relevant Experience (Yrs) cannot be negative.')
            if rec.x_total_experience == 0:
                raise ValidationError('Total Experience (Yrs) is required and cannot be 0.')
            if rec.x_relevant_experience == 0:
                raise ValidationError('Relevant Experience (Yrs) is required and cannot be 0.')
            if rec.x_relevant_experience > rec.x_total_experience:
                raise ValidationError(
                    'Relevant Experience (Yrs) cannot be greater than Total Experience (Yrs).'
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
            ('15_days',           '15 Days'),
            ('30_days',           '30 Days'),
            ('60_days',           '60 Days'),
            ('90_days',           '90 Days'),
            ('immediate_joiner',  'Immediate Joiner'),
            ('serving_notice',    'Serving Notice Period'),
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

    @api.constrains('x_current_ctc_lpa', 'x_expected_ctc_lpa')
    def _check_ctc_not_negative(self):
        # Enforced as "> 0" rather than ">= 0": these fields are marked
        # required="1" in the form, but a Float widget is pre-filled with
        # 0.0 as soon as the record is opened, so "required" alone never
        # catches a user who leaves the default untouched. Rejecting 0
        # here is what actually makes the field mandatory in practice.
        for rec in self:
            if rec.x_current_ctc_lpa < 0:
                raise ValidationError('Current CTC (LPA) cannot be negative.')
            if rec.x_expected_ctc_lpa < 0:
                raise ValidationError('Expected CTC (LPA) cannot be negative.')
            if rec.x_current_ctc_lpa == 0:
                raise ValidationError('Current CTC (LPA) is required and cannot be 0.')
            if rec.x_expected_ctc_lpa == 0:
                raise ValidationError('Expected CTC (LPA) is required and cannot be 0.')

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

    def action_open_linkedin(self):
        self.ensure_one()
        if self.linkedin_profile:
            url = self.linkedin_profile
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }

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

    # ── Referral Attribution ──────────────────────────────────────
    x_is_referral = fields.Boolean(
        string='Is Referral',
        default=False,
        help='Check this if the candidate was referred by an employee.',
    )

    x_referred_by_id = fields.Many2one(
        'hr.employee',
        string='Referred By',
        domain="[('user_id.share', '=', False)]",
        help='Internal employee who referred this candidate.',
    )

    @api.constrains('x_is_referral', 'x_referred_by_id')
    def _check_referred_by_required(self):
        for rec in self:
            if rec.x_is_referral and not rec.x_referred_by_id:
                raise ValidationError(
                    'Please select "Referred By" when marking a candidate as a referral.'
                )

    @api.onchange('x_is_referral')
    def _onchange_is_referral_clear_referrer(self):
        if not self.x_is_referral:
            self.x_referred_by_id = False

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

    @api.onchange('x_notice_period')
    def _onchange_notice_period_clear_lwd(self):
        """Clear Last Working Date when the notice period type doesn't need it.
        Keeps the value only for 'Serving Notice Period' and 'Immediate Joiner'."""
        if self.x_notice_period not in ('serving_notice', 'immediate_joiner'):
            self.x_lwd = False

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
