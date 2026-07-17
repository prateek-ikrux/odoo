# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api
from .assessment_report_xlsx import build_assessment_xlsx
from .pipeline_constants import ROLE_STATUS_LABELS, SUB_STATUS_LABELS, SUB_STATUS_SELECTION, EMP_TYPE_LABELS


class AssessmentReportWizard(models.TransientModel):
    _name = 'recruitment.assessment.report.wizard'
    _description = 'Internal Assessment Report Export Wizard'

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
    sub_status     = fields.Selection(
        SUB_STATUS_SELECTION,
        string='Role Status Remarks',
    )
    employment_type = fields.Selection(
        list(EMP_TYPE_LABELS.items()),
        string='Employment Type',
    )
    stage_ids      = fields.Many2many('hr.recruitment.stage', string='Stages')

    # ── Assessment Filters ────────────────────────────────────────
    assessment_link_received = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='Assessment Link Received',
    )
    assessment_taken = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='Assessment Taken',
    )
    assessment_feedback = fields.Selection(
        [('select', 'Select'), ('reject', 'Reject')],
        string='Assessment Feedback',
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
        if self.sub_status:
            domain.append(('job_id.x_sub_status', '=', self.sub_status))
        if self.employment_type:
            domain.append(('job_id.x_employment_type', '=', self.employment_type))
        if self.stage_ids:
            domain.append(('stage_id', 'in', self.stage_ids.ids))
        if self.assessment_link_received:
            domain.append(('x_assessment_link_received', '=', self.assessment_link_received))
        if self.assessment_taken:
            domain.append(('x_assessment_taken', '=', self.assessment_taken))
        if self.assessment_feedback:
            domain.append(('x_assessment_feedback', '=', self.assessment_feedback))
        return domain

    def _get_report_data(self):
        applicants = self.env['hr.applicant'].search(
            self._base_domain(),
            order='department_id asc, job_id asc, id asc',
        )

        # Assessment-related stage names (used for current hiring status check)
        assessment_stages = {'Assessment Link Shared', 'Assessment Reject'}

        rows = []
        for seq, app in enumerate(applicants, start=1):
            job  = app.job_id
            dept = app.department_id

            req_id      = job.x_req_id      if job else ''
            client      = dept.name          if dept else ''
            role        = job.name           if job else ''
            role_type   = EMP_TYPE_LABELS.get(job.x_employment_type, 'Consulting') if job else 'Consulting'
            role_status = ROLE_STATUS_LABELS.get(app.x_role_status, '') if app.x_role_status else ''
            sub_status  = SUB_STATUS_LABELS.get(app.x_sub_status, '') if app.x_sub_status else ''

            candidate_name   = app.partner_name or ''
            current_status   = app.stage_id.name if app.stage_id else ''

            link_received = app.x_assessment_link_received or 'no'
            taken         = app.x_assessment_taken         or 'no'
            feedback_raw  = app.x_assessment_feedback

            # Determine display values with N/A cascade logic:
            # If assessment link received = No → taken and feedback are N/A
            # If assessment link received = Yes but taken = No → feedback is N/A
            link_received_display = 'Yes' if link_received == 'yes' else 'No'

            if link_received != 'yes':
                taken_display    = 'N/A'
                feedback_display = 'N/A'
            else:
                taken_display = 'Yes' if taken == 'yes' else 'No'
                if taken != 'yes':
                    feedback_display = 'N/A'
                else:
                    feedback_map = {'select': 'Select', 'reject': 'Reject'}
                    feedback_display = feedback_map.get(feedback_raw, 'N/A') if feedback_raw else 'N/A'

            rows.append({
                'seq':                      seq,
                'req_id':                   req_id,
                'client':                   client,
                'role':                     role,
                'role_type':                role_type,
                'role_status':              role_status,
                'sub_status':               sub_status,
                'candidate_name':           candidate_name,
                'assessment_link_received': link_received_display,
                'assessment_taken':         taken_display,
                'assessment_feedback':      feedback_display,
                'current_hiring_status':    current_status,
            })

        return rows

    def action_export_xlsx(self):
        """Export Internal Assessment Report to Excel."""
        rows = self._get_report_data()
        xlsx_data = build_assessment_xlsx(rows)
        attachment = self.env['ir.attachment'].create({
            'name': 'Internal_Assessment_Report.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

