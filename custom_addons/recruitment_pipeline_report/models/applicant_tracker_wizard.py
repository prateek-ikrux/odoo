# -*- coding: utf-8 -*-
import base64

from odoo import models, fields
from .applicant_tracker_xlsx import build_tracker_xlsx


class ApplicantTrackerWizard(models.TransientModel):
    _name = 'recruitment.applicant.tracker.wizard'
    _description = 'Applicant Tracker Export Wizard'

    date_from      = fields.Date(string='Date From')
    date_to        = fields.Date(string='Date To')
    department_ids = fields.Many2many('hr.department', string='Clients')
    job_ids        = fields.Many2many('hr.job',        string='Roles')
    recruiter_ids  = fields.Many2many('res.users',     string='Recruiters')

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

            budget = app.x_budget_display or ''
            bill_rate = app.x_bill_rate_display or ''

            # Current Status = current stage name
            current_status = app.stage_id.name if app.stage_id else ''

            # Recruiter display (TE / Recruiter column)
            recruiter = app.user_id.name if app.user_id else ''
            lwd = app.x_lwd.strftime('%d/%m/%Y') if app.x_lwd else ''

            # Source
            source = app.source_id.name if app.source_id else ''

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
                'application_date':       app.create_date.strftime('%d/%m/%Y') if app.create_date else '',
                'current_status':         current_status,
                'client_portal_status':   dict(app._fields['x_client_portal_status'].selection).get(
                                              app.x_client_portal_status, 'Not Uploaded'
                                          ),
                # Candidate Details
                'candidate_name':         app.partner_name          or '',
                'candidate_number':       app.partner_phone         or '',
                'candidate_email':        app.email_from            or '',
                'skill':                  app.x_skill               or '',
                'total_experience':       app.x_total_experience    or '',
                'relevant_experience':    app.x_relevant_experience or '',
                'current_organization':   app.x_current_organization or '',
                'designation':            app.x_designation          or '',
                'education':              app.x_education            or '',
                # Location & Availability
                'current_location':       app.x_current_location    or '',
                'preferred_location':     app.x_preferred_location  or '',
                'notice_period':          app.x_notice_period       or '',
                'lwd':                    lwd,
                # Compensation
                'current_ctc':            app.x_current_ctc         or '',
                'expected_ctc':           app.x_expected_ctc        or '',
                'budget':                 budget,
                'bill_rate':              bill_rate,
                'offer_in_hand':          app.x_offer_in_hand       or '',
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
