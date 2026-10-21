# -*- coding: utf-8 -*-

from odoo import models, fields, tools
from psycopg2 import sql as psql

from .pipeline_constants import (
    ROLE_STATUS_SELECTION,
    SUB_STATUS_SELECTION,
    EMP_TYPE_LABELS,
)


class RecruitmentPipelineSummaryView(models.Model):
    _name = 'recruitment.pipeline.summary.view'
    _description = 'Pipeline Summary (Pivot/List)'
    _auto = False
    _rec_name = 'role'

    client          = fields.Char(string='Client',         readonly=True)
    poc             = fields.Char(string='POC',            readonly=True)
    role            = fields.Char(string='Role',           readonly=True)
    role_type       = fields.Selection(
        list(EMP_TYPE_LABELS.items()),
        string='Role Type', readonly=True,
    )
    role_status     = fields.Selection(
        ROLE_STATUS_SELECTION,
        string='Role Status', readonly=True,
    )
    sub_status      = fields.Selection(
        SUB_STATUS_SELECTION,
        string='Role Status Remarks', readonly=True,
    )
    role_received_date = fields.Date(string='Role Received from Client', readonly=True)
    role_opened_date   = fields.Date(string='Role Opened to Team',       readonly=True)
    no_of_positions = fields.Integer(string='No. of Positions', readonly=True, aggregator='max')
    department_id   = fields.Many2one('hr.department', readonly=True)
    job_id          = fields.Many2one('hr.job',        readonly=True)
    stage_id        = fields.Many2one('hr.recruitment.stage', string='Stage', readonly=True)
    applicant_count = fields.Integer(string='Applicants', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        query = psql.SQL("""
            CREATE OR REPLACE VIEW {table} AS (
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY d.name->>'en_US', j.name->>'en_US', s.sequence
                    )                                           AS id,
                    MAX(d.id)                                   AS department_id,
                    j.id                                        AS job_id,
                    s.id                                        AS stage_id,
                    COALESCE(d.name->>'en_US', 'N/A')          AS client,
                    COALESCE(poc.name,         'N/A')          AS poc,
                    COALESCE(j.name->>'en_US', 'N/A')          AS role,
                    COALESCE(j.x_employment_type, 'fte')       AS role_type,
                    COALESCE(j.x_role_status, 'active')        AS role_status,
                    j.x_sub_status                             AS sub_status,
                    j.x_role_received_date                     AS role_received_date,
                    j.x_role_opened_date                       AS role_opened_date,
                    COALESCE(j.no_of_recruitment, 0)           AS no_of_positions,
                    COUNT(a.id)                                AS applicant_count

                FROM hr_applicant a
                JOIN  hr_job                   j  ON j.id  = a.job_id
                LEFT JOIN hr_department        d  ON d.id  = a.department_id
                LEFT JOIN hr_recruitment_stage s  ON s.id  = a.stage_id
                LEFT JOIN res_partner          poc ON poc.id = j.x_poc_id
                GROUP BY COALESCE(d.id, 0), d.name, j.id, j.name, j.x_employment_type,
                         j.x_role_status, j.x_sub_status,
                         j.x_role_received_date, j.x_role_opened_date,
                         j.no_of_recruitment, poc.id, poc.name, s.id, s.sequence
            )
        """).format(
            table=psql.Identifier(self._table),
        )

        self.env.cr.execute(query)

    def action_open_export_wizard(self):
        """Open export wizard with date range, client, and role filters."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Pipeline Summary',
            'res_model': 'recruitment.pipeline.summary.wizard',
            'view_mode': 'form',
            'target': 'new',
            'views': [(
                self.env.ref(
                    'recruitment_pipeline_report.view_pipeline_summary_export_wizard_form'
                ).id, 'form',
            )],
        }
