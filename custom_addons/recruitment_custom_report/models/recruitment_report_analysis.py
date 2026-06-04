# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class RecruitmentReportAnalysis(models.Model):
    _name = 'recruitment.report.analysis'
    _description = 'Recruitment Report Analysis'
    _auto = False
    _rec_name = 'job_name'
    _order = 'create_date desc'

    job_name = fields.Char(string='Job Position', readonly=True)
    department_name = fields.Char(string='Department', readonly=True)
    stage_name = fields.Char(string='Stage', readonly=True)
    applicant_name = fields.Char(string='Applicant Name', readonly=True)
    partner_name = fields.Char(string='Contact Name', readonly=True)
    priority = fields.Selection(
        selection=[('0', 'Normal'), ('1', 'Good'), ('2', 'Very Good'), ('3', 'Excellent')],
        string='Priority', readonly=True,
    )
    active = fields.Boolean(string='Active', readonly=True)
    create_date = fields.Datetime(string='Applied Date', readonly=True)
    date_closed = fields.Datetime(string='Date Closed', readonly=True)
    user_id = fields.Many2one('res.users', string='Responsible', readonly=True)
    job_id = fields.Many2one('hr.job', string='Job Position (M2O)', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department (M2O)', readonly=True)
    stage_id = fields.Many2one('hr.recruitment.stage', string='Stage (M2O)', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', string='Refuse Reason', readonly=True)
    nb_applicants = fields.Integer(string='# Applicants', readonly=True)
    delay_close = fields.Float(string='Days to Close', digits=(16, 2), readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    a.id,
                    j.name                                  AS job_name,
                    d.name                                  AS department_name,
                    s.name                                  AS stage_name,
                    a.partner_name                          AS applicant_name,
                    p.name                                  AS partner_name,
                    a.priority,
                    a.active,
                    a.create_date,
                    a.date_closed,
                    a.user_id,
                    a.job_id,
                    a.department_id,
                    a.stage_id,
                    a.company_id,
                    a.refuse_reason_id,
                    1                                       AS nb_applicants,
                    EXTRACT(EPOCH FROM (a.date_closed - a.create_date)) / 86400.0
                                                            AS delay_close
                FROM hr_applicant a
                LEFT JOIN hr_job j           ON j.id = a.job_id
                LEFT JOIN hr_department d    ON d.id = a.department_id
                LEFT JOIN hr_recruitment_stage s ON s.id = a.stage_id
                LEFT JOIN res_partner p      ON p.id = a.partner_id
            )
        """ % self._table)
