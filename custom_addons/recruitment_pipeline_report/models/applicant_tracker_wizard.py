# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api
from .applicant_tracker_xlsx import build_tracker_xlsx


class ApplicantTrackerWizard(models.TransientModel):
    _name = 'recruitment.applicant.tracker.wizard'
    _description = 'Applicant Tracker Export Wizard'

    # ── Date Range ────────────────────────────────────────────────
    date_from      = fields.Date(string='Date From')
    date_to        = fields.Date(string='Date To')

    # ── Role Filters ──────────────────────────────────────────────
    department_ids = fields.Many2many('hr.department', string='Clients')
    job_ids        = fields.Many2many('hr.job',        string='Roles')
    job_ids_domain = fields.Binary(compute='_compute_job_ids_domain')
    recruiter_ids  = fields.Many2many('res.users',     string='Recruiters')
    role_status    = fields.Selection(
        [
            ('active',      'Active'),
            ('in_progress', 'In Progress'),
            ('on_hold',     'On Hold'),
            ('closed',      'Closed'),
        ],
        string='Role Status',
    )
    employment_type = fields.Selection(
        [('fte', 'FTE'), ('consulting', 'Consulting')],
        string='Employment Type',
    )
    stage_ids      = fields.Many2many('hr.recruitment.stage', string='Stages')

    # ── Candidate Filters ─────────────────────────────────────────
    source_ids     = fields.Many2many('utm.source', string='Sources')
    location_ids   = fields.Many2many('recruitment.city', string='Current Locations')
    skill_ids      = fields.Many2many('recruitment.skill', string='Skills')
    notice_period  = fields.Selection(
        [
            ('15_days',          '15 Days'),
            ('30_days',          '30 Days'),
            ('60_days',          '60 Days'),
            ('90_days',          '90 Days'),
            ('immediate_joiner', 'Immediate Joiner'),
            ('serving_notice',   'Serving Notice Period'),
        ],
        string='Notice Period',
    )
    client_portal_status = fields.Selection(
        [
            ('uploaded',     'Uploaded'),
            ('not_uploaded', 'Not Uploaded'),
        ],
        string='Client Portal Status',
    )

    # ── Dynamic domains ──────────────────────────────────────────
    @api.depends('department_ids')
    def _compute_job_ids_domain(self):
        for rec in self:
            if rec.department_ids:
                rec.job_ids_domain = [('department_id', 'in', rec.department_ids.ids)]
            else:
                rec.job_ids_domain = []

    def _base_domain(self):
        domain = [('active', 'in', [True, False])]
        if self.date_from:
            domain.append(('create_date', '>=', str(self.date_from) + ' 00:00:00'))
        if self.date_to:
            domain.append(('create_date', '<=', str(self.date_to) + ' 23:59:59'))
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        if self.job_ids:
            domain.append(('job_id', 'in', self.job_ids.ids))
        if self.recruiter_ids:
            domain.append(('user_id', 'in', self.recruiter_ids.ids))
        if self.role_status:
            domain.append(('job_id.x_role_status', '=', self.role_status))
        if self.employment_type:
            domain.append(('job_id.x_employment_type', '=', self.employment_type))
        if self.stage_ids:
            domain.append(('stage_id', 'in', self.stage_ids.ids))
        if self.source_ids:
            domain.append(('source_id', 'in', self.source_ids.ids))
        if self.location_ids:
            domain.append(('x_current_location_id', 'in', self.location_ids.ids))
        if self.skill_ids:
            domain.append(('x_skill_ids', 'in', self.skill_ids.ids))
        if self.notice_period:
            domain.append(('x_notice_period', '=', self.notice_period))
        if self.client_portal_status:
            domain.append(('x_client_portal_status', '=', self.client_portal_status))
        return domain

    def _get_report_data(self):
        applicants = self.env['hr.applicant'].search(
            self._base_domain(),
            order='department_id asc, job_id asc, id asc',
        )

        rows = []
        for seq, app in enumerate(applicants, start=1):
            job  = app.job_id
            dept = app.department_id
            emp_type = job.x_employment_type if job else 'fte'

            # Current Status = current stage name
            current_status = app.stage_id.name if app.stage_id else ''

            # Recruiter display (TE / Recruiter column)
            recruiter = app.user_id.name if app.user_id else ''

            # Source
            source = app.source_id.name if app.source_id else ''

            def format_ordinal_date(d):
                if not d: return ''
                day = d.day
                if 4 <= day <= 20 or 24 <= day <= 30:
                    suf = "th"
                else:
                    suf = ["st", "nd", "rd"][day % 10 - 1]
                return d.strftime(f"{day}{suf} %B %Y")

            rows.append({
                'seq':                    seq,
                # Requisition Details
                'req_id':                 job.x_req_id              if job else '',
                'client':                 dept.name                 if dept else '',
                'role':                   job.name                  if job else '',
                'role_type':              'FTE' if emp_type == 'fte' else 'Consulting',
                'recruiter':              recruiter,
                # Application Details
                'source':                 source,
                'application_date':       format_ordinal_date(app.create_date),
                'current_status':         current_status,
                'client_portal_status':   dict(app._fields['x_client_portal_status'].selection).get(
                                              app.x_client_portal_status, 'Not Uploaded'
                                          ),
                # Candidate Details
                'candidate_name':         app.partner_name          or '',
                'candidate_number':       app.partner_phone         or '',
                'candidate_email':        app.email_from            or '',
                'skill':                  ', '.join(app.x_skill_ids.mapped('name')) if app.x_skill_ids else '',
                'total_experience':       app.x_total_experience    or '',
                'relevant_experience':    app.x_relevant_experience or '',
                'current_organization':   app.x_current_organization or '',
                'designation':            app.x_designation         or '',
                'education':              app.x_education           or '',
                
                # Location & Availability
                'current_location':       app.x_current_location_id.name if app.x_current_location_id else '',
                'preferred_location':     'Anywhere' if app.x_open_to_anywhere else (', '.join(app.x_preferred_location_ids.mapped('name')) if app.x_preferred_location_ids else ''),
                'notice_period':          dict(app._fields['x_notice_period'].selection).get(app.x_notice_period, '') if app.x_notice_period else '',
                'lwd':                    format_ordinal_date(app.x_lwd) if app.x_notice_period in ('serving_notice', 'immediate_joiner') else 'N/A',
                # Compensation
                'current_ctc':            app.x_current_ctc_lpa     if app.x_current_ctc_lpa else '',
                'expected_ctc':           app.x_expected_ctc_lpa    if app.x_expected_ctc_lpa else '',
                'budget':                 app.x_budget_lpa_display  if app.x_budget_lpa_display else '',
                'bill_rate':              app.x_bill_rate_lpm_display if app.x_bill_rate_lpm_display else '',
                'offer_in_hand':          ', '.join(app.x_offer_in_hand_ids.mapped('name')) if app.x_offer_in_hand_ids else '',
                # Additional Information
                'reason_for_job_change':  app.x_reason_for_job_change or '',
                'remarks':                app.x_remarks              or '',
            })

        return rows

    def action_export_xlsx(self):
        """Export filtered applicant tracker to Excel."""
        rows = self._get_report_data()
        xlsx_data = build_tracker_xlsx(rows)
        attachment = self.env['ir.attachment'].create({
            'name': 'Applicant_Tracker.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

