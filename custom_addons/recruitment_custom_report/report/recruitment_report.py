# -*- coding: utf-8 -*-
from datetime import datetime, time

from odoo import api, fields, models


class RecruitmentReportMixin(models.AbstractModel):
    _name = 'report.recruitment_custom_report.rpt_mixin'
    _description = 'Shared helpers for recruitment PDF reports'

    @api.model
    def _domain_from_report_data(self, data):
        """Build a search domain from wizard payload in ``data``."""
        if not data:
            return []
        domain = []
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            if isinstance(date_to, str):
                date_to = fields.Date.from_string(date_to)
            domain.append(('create_date', '<=', datetime.combine(date_to, time.max)))
        job_ids = data.get('job_ids')
        if job_ids:
            domain.append(('job_id', 'in', job_ids))
        department_ids = data.get('department_ids')
        if department_ids:
            domain.append(('department_id', 'in', department_ids))
        stage_ids = data.get('stage_ids')
        if stage_ids:
            domain.append(('stage_id', 'in', stage_ids))
        return domain

    @api.model
    def _resolve_applicant_docs(self, docids, data=None):
        data = dict(data or {})
        Applicant = self.env['hr.applicant']

        applicant_ids = data.get('applicant_ids')
        if applicant_ids:
            return Applicant.browse(applicant_ids)

        if docids:
            docs = Applicant.browse(docids)
            if docs.exists():
                return docs

        domain = self._domain_from_report_data(data)
        if domain or data.get('date_from') or data.get('date_to'):
            return Applicant.search(domain)
        return Applicant.search([])

    @api.model
    def _recruitment_report_values(self, docids, data=None):
        data = dict(data or {})
        docs = self._resolve_applicant_docs(docids, data)
        companies = docs.company_id
        if len(companies) == 1:
            company = companies.sudo()
        else:
            company = self.env.company.sudo()
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.applicant',
            'docs': docs,
            'doc': docs[:1],
            'company': company,
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to'),
        }


class ReportRecruitmentPipeline(models.AbstractModel):
    _name = 'report.recruitment_custom_report.rpt_pipeline'
    _inherit = 'report.recruitment_custom_report.rpt_mixin'
    _description = 'Recruitment Pipeline Summary Report'

    def _get_report_values(self, docids, data=None):
        return self._recruitment_report_values(docids, data)


class ReportRecruitmentStageAnalysis(models.AbstractModel):
    _name = 'report.recruitment_custom_report.rpt_stage'
    _inherit = 'report.recruitment_custom_report.rpt_mixin'
    _description = 'Stage-wise Recruitment Analysis Report'

    def _get_report_values(self, docids, data=None):
        return self._recruitment_report_values(docids, data)


class ReportRecruitmentActivity(models.AbstractModel):
    _name = 'report.recruitment_custom_report.rpt_activity'
    _inherit = 'report.recruitment_custom_report.rpt_mixin'
    _description = 'Recruitment Activity Report'

    def _get_report_values(self, docids, data=None):
        return self._recruitment_report_values(docids, data)


class ReportRecruitmentApplicantStatus(models.AbstractModel):
    _name = 'report.recruitment_custom_report.rpt_status'
    _inherit = 'report.recruitment_custom_report.rpt_mixin'
    _description = 'Applicant Status Report'

    def _get_report_values(self, docids, data=None):
        return self._recruitment_report_values(docids, data)
