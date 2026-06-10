# -*- coding: utf-8 -*-

from odoo import models, fields, tools
from psycopg2 import sql as psql

from .pipeline_constants import (
    ROLE_STATUS_SELECTION,
    SUB_STATUS_SELECTION,
    MEASURE_FIELDS,
    STAGE_BY_FIELD,
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
        [('fte', 'FTE'), ('consulting', 'Consulting')],
        string='Role Type', readonly=True,
    )
    role_status     = fields.Selection(
        ROLE_STATUS_SELECTION,
        string='Role Status', readonly=True,
    )
    sub_status      = fields.Selection(
        SUB_STATUS_SELECTION,
        string='Sub Status', readonly=True,
    )
    no_of_positions = fields.Integer(string='No. of Positions', readonly=True)
    department_id   = fields.Many2one('hr.department', readonly=True)
    job_id          = fields.Many2one('hr.job',        readonly=True)

    profiles_shared        = fields.Integer(string='Profiles Shared',               readonly=True)
    screening_pending      = fields.Integer(string='Screening Pending',              readonly=True)
    duplicate_profiles     = fields.Integer(string='Duplicate Profiles',             readonly=True)
    assessment_link_shared = fields.Integer(string='Assessment Link Shared',         readonly=True)
    assessment_reject      = fields.Integer(string='Assessment Reject',              readonly=True)
    l1_tbs                 = fields.Integer(string='L1 TBS',                         readonly=True)
    l1_slot_shared         = fields.Integer(string='L1 Slot Shared',                 readonly=True)
    l1_scheduled           = fields.Integer(string='L1 Scheduled',                   readonly=True)
    l1_feedback_pending    = fields.Integer(string='L1 Feedback Pending',            readonly=True)
    l1_reject              = fields.Integer(string='L1 Reject',                      readonly=True)
    l2_tbs                 = fields.Integer(string='L2 TBS',                         readonly=True)
    l2_slot_shared         = fields.Integer(string='L2 Slot Shared',                 readonly=True)
    l2_scheduled           = fields.Integer(string='L2 Scheduled',                   readonly=True)
    l2_feedback_pending    = fields.Integer(string='L2 Feedback Pending',            readonly=True)
    l2_reject              = fields.Integer(string='L2 Reject',                      readonly=True)
    cr_tbs                 = fields.Integer(string='Client Round TBS',               readonly=True)
    cr_slot_shared         = fields.Integer(string='Client Round Slot Shared',       readonly=True)
    cr_scheduled           = fields.Integer(string='Client Round Scheduled',         readonly=True)
    cr_feedback_pending    = fields.Integer(string='Client Round Feedback Pending',  readonly=True)
    cr_reject              = fields.Integer(string='Client Round Reject',            readonly=True)
    tbo                    = fields.Integer(string='TBO',                            readonly=True)
    offered                = fields.Integer(string='Offered/Yet to Join',            readonly=True)
    joined                 = fields.Integer(string='Joined',                         readonly=True)
    declined               = fields.Integer(string='Declined',                       readonly=True)
    quit_post_joining      = fields.Integer(string='Quit Post Joining',              readonly=True)

    @staticmethod
    def _stage_count_sql_fragments():
        """Build COUNT(*) FILTER fragments from the canonical stage name map."""
        parts = []
        for field_name in MEASURE_FIELDS:
            stage_name = STAGE_BY_FIELD[field_name]
            parts.append(
                psql.SQL("COUNT(*) FILTER (WHERE s.name->>'en_US' = {}) AS {}").format(
                    psql.Literal(stage_name),
                    psql.Identifier(field_name),
                )
            )
        return psql.SQL(',\n                    ').join(parts)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        stage_counts = self._stage_count_sql_fragments()

        query = psql.SQL("""
            CREATE OR REPLACE VIEW {table} AS (
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY d.name->>'en_US', j.name->>'en_US'
                    )                                           AS id,
                    MAX(d.id)                                   AS department_id,
                    j.id                                        AS job_id,
                    COALESCE(d.name->>'en_US', 'N/A')          AS client,
                    COALESCE(poc.name,         'N/A')          AS poc,
                    COALESCE(j.name->>'en_US', 'N/A')          AS role,
                    COALESCE(j.x_employment_type, 'fte')       AS role_type,
                    COALESCE(j.x_role_status, 'active')        AS role_status,
                    j.x_sub_status                             AS sub_status,
                    COALESCE(j.no_of_recruitment, 0)           AS no_of_positions,
                    {stage_counts}

                FROM hr_applicant a
                JOIN  hr_job                   j  ON j.id  = a.job_id
                LEFT JOIN hr_department        d  ON d.id  = a.department_id
                LEFT JOIN hr_recruitment_stage s  ON s.id  = a.stage_id
                LEFT JOIN res_partner          poc ON poc.id = j.x_poc_id
                GROUP BY COALESCE(d.id, 0), d.name, j.id, j.name, j.x_employment_type,
                         j.x_role_status, j.x_sub_status,
                         j.no_of_recruitment, poc.id, poc.name
            )
        """).format(
            table=psql.Identifier(self._table),
            stage_counts=stage_counts,
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
