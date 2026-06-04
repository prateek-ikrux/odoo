# -*- coding: utf-8 -*-
from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class RecruitmentReportWizard(models.TransientModel):
    _name = 'recruitment.report.wizard'
    _description = 'Recruitment Report Wizard'

    def _default_date_from(self):
        today = fields.Date.context_today(self)
        return today.replace(month=1, day=1)

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=_default_date_from,
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today,
    )
    job_ids = fields.Many2many(
        'hr.job',
        string='Job Positions',
        help='Leave empty to include all job positions.',
    )
    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Leave empty to include all departments.',
    )
    stage_ids = fields.Many2many(
        'hr.recruitment.stage',
        string='Stages',
        help='Leave empty to include all stages.',
    )
    report_type = fields.Selection(
        selection=[
            ('pipeline', 'Pipeline Summary'),
            ('stage_analysis', 'Stage-wise Analysis'),
            ('activity', 'Recruitment Activity'),
            ('applicant_status', 'Applicant Status'),
        ],
        string='Report Type',
        default='pipeline',
        required=True,
    )
    date_filter_type = fields.Selection(
        selection=[
            ('creation', 'By Creation Date (When Sourced/Added)'),
            ('modification', 'By Modification Date (Status Changes)'),
        ],
        string='Date Filter Basis',
        default='creation',
        required=True,
        help='Creation: candidates added during the period; Modification: status changes during the period',
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validate that date_from is not greater than date_to."""
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError(
                    _('"Date From" cannot be greater than "Date To". '
                      'Please ensure from_date ≤ to_date.')
                )

    def _get_applicants(self):
        self.ensure_one()
        # Select date field based on filter type
        date_field = 'write_date' if self.date_filter_type == 'modification' else 'create_date'
        domain = [
            (date_field, '>=', datetime.combine(self.date_from, time.min)),
            (date_field, '<=', datetime.combine(self.date_to, time.max)),
        ]
        if self.job_ids:
            domain.append(('job_id', 'in', self.job_ids.ids))
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        if self.stage_ids:
            domain.append(('stage_id', 'in', self.stage_ids.ids))
        return self.env['hr.applicant'].search(domain)

    def _report_data(self, applicants):
        self.ensure_one()
        return {
            'date_from': fields.Date.to_string(self.date_from),
            'date_to': fields.Date.to_string(self.date_to),
            'date_filter_type': self.date_filter_type,
            'applicant_ids': applicants.ids,
            'job_ids': self.job_ids.ids,
            'department_ids': self.department_ids.ids,
            'stage_ids': self.stage_ids.ids,
        }

    def action_print_report(self):
        self.ensure_one()
        applicants = self._get_applicants()
        if not applicants:
            raise UserError(_(
                'No applicants match the selected filters. '
                'Try widening the date range or clearing optional filters.'
            ))
        report_map = {
            'pipeline': 'recruitment_custom_report.action_report_recruitment_pipeline',
            'stage_analysis': 'recruitment_custom_report.action_report_recruitment_stage_analysis',
            'activity': 'recruitment_custom_report.action_report_recruitment_activity',
            'applicant_status': 'recruitment_custom_report.action_report_recruitment_applicant_status',
        }
        return self.env.ref(report_map[self.report_type]).report_action(
            applicants,
            data=self._report_data(applicants),
        )

    def action_preview_report(self):
        return self.action_print_report()
