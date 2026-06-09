# -*- coding: utf-8 -*-
import base64
import io

from odoo import models, fields, tools, api
from psycopg2 import sql as psql

from .pipeline_constants import (
    ROLE_STATUS_SELECTION,
    SUB_STATUS_SELECTION,
    PRIMARY_HEADERS,
    SECONDARY_HEADERS,
    MEASURE_FIELDS,
    ROLE_STATUS_LABELS,
    SUB_STATUS_LABELS,
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
    cr_scheduled           = fields.Integer(string='Client Round Scheduled',         readonly=True)
    cr_feedback_pending    = fields.Integer(string='Client Round Feedback Pending',  readonly=True)
    cr_reject              = fields.Integer(string='Client Round Reject',            readonly=True)
    tbo                    = fields.Integer(string='TBO',                            readonly=True)
    offered                = fields.Integer(string='Offered/Yet to Join',            readonly=True)
    joined                 = fields.Integer(string='Joined',                         readonly=True)
    declined               = fields.Integer(string='Declined',                       readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        query = psql.SQL("""
            CREATE OR REPLACE VIEW {table} AS (
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY d.name->>'en_US', j.name->>'en_US'
                    )                                           AS id,
                    d.id                                        AS department_id,
                    j.id                                        AS job_id,
                    COALESCE(d.name->>'en_US', 'N/A')          AS client,
                    COALESCE(u.name,           'N/A')          AS poc,
                    COALESCE(j.name->>'en_US', 'N/A')          AS role,
                    COALESCE(j.x_employment_type, 'fte')       AS role_type,
                    COALESCE(j.x_role_status, 'active')        AS role_status,
                    j.x_sub_status                             AS sub_status,
                    COALESCE(j.no_of_recruitment, 0)           AS no_of_positions,

                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'New')
                                                                AS profiles_shared,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'Screening Pending')
                                                                AS screening_pending,
                    0                                           AS duplicate_profiles,
                    0                                           AS assessment_link_shared,
                    0                                           AS assessment_reject,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'L1 to be Scheduled')
                                                                AS l1_tbs,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'L1 Slot Shared')
                                                                AS l1_slot_shared,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'L1 Scheduled')
                                                                AS l1_scheduled,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'L1 Feedback Pending')
                                                                AS l1_feedback_pending,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'L1 Reject')
                                                                AS l1_reject,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'L2 to be Scheduled')
                                                                AS l2_tbs,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'L2 Slot Shared')
                                                                AS l2_slot_shared,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'L2 Scheduled')
                                                                AS l2_scheduled,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'L2 Feedback Pending')
                                                                AS l2_feedback_pending,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'L2 Reject')
                                                                AS l2_reject,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'Client Round TBS')
                                                                AS cr_tbs,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'Client Round Scheduled')
                                                                AS cr_scheduled,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'Client Round Feedback Pending')
                                                                AS cr_feedback_pending,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'Client Round Reject')
                                                                AS cr_reject,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'TBO')
                                                                AS tbo,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'Offered')
                                                                AS offered,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'Joined')
                                                                AS joined,
                    COUNT(*) FILTER (WHERE s.name->>'en_US' = 'Declined')
                                                                AS declined

                FROM hr_applicant a
                JOIN  hr_department            d  ON d.id  = a.department_id
                JOIN  hr_job                   j  ON j.id  = a.job_id
                LEFT JOIN hr_recruitment_stage s  ON s.id  = a.stage_id
                LEFT JOIN res_users            pu ON pu.id = j.x_poc_id
                LEFT JOIN res_partner          u  ON u.id  = pu.partner_id
                GROUP BY d.id, d.name, j.id, j.name, j.x_employment_type,
                         j.x_role_status, j.x_sub_status,
                         j.no_of_recruitment, pu.id, u.name
            )
        """).format(table=psql.Identifier(self._table))

        self.env.cr.execute(query)

    @api.model
    def _generate_xlsx_bytes(self):
        """Build pipeline summary XLSX with two-row headers."""
        import xlsxwriter  # noqa: PLC0415

        records = self.search([], order='client, role')
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Pipeline Summary')

        primary_fmt = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#2C3E50', 'font_color': '#FFFFFF',
            'border': 1, 'text_wrap': True,
        })
        pipeline_hdr_fmt = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#1A6B9A', 'font_color': '#FFFFFF',
            'border': 1,
        })
        secondary_fmt = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#F0F3F4', 'border': 1, 'text_wrap': True,
        })
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        num_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})

        identity_count = len(PRIMARY_HEADERS)
        measure_count = len(SECONDARY_HEADERS)

        for col, title in enumerate(PRIMARY_HEADERS):
            worksheet.write(0, col, title, primary_fmt)
        worksheet.merge_range(
            0, identity_count, 0, identity_count + measure_count - 1,
            'Pipeline Summary', pipeline_hdr_fmt,
        )
        for col in range(identity_count):
            worksheet.write(1, col, '', secondary_fmt)
        for col, title in enumerate(SECONDARY_HEADERS, start=identity_count):
            worksheet.write(1, col, title, secondary_fmt)

        for row_idx, rec in enumerate(records, start=2):
            identity_values = [
                row_idx - 1,
                rec.client or '',
                rec.poc or '',
                rec.role or '',
                EMP_TYPE_LABELS.get(rec.role_type, rec.role_type or ''),
                ROLE_STATUS_LABELS.get(rec.role_status, rec.role_status or ''),
                SUB_STATUS_LABELS.get(rec.sub_status, rec.sub_status or ''),
                rec.no_of_positions or 0,
            ]
            for col, val in enumerate(identity_values):
                fmt = num_fmt if col in (0, 7) else cell_fmt
                worksheet.write(row_idx, col, val, fmt)
            for col, field_name in enumerate(MEASURE_FIELDS, start=identity_count):
                worksheet.write(row_idx, col, getattr(rec, field_name, 0) or 0, num_fmt)

        worksheet.set_column(0, 0, 4)
        worksheet.set_column(1, 3, 18)
        worksheet.set_column(4, 7, 12)
        worksheet.set_column(identity_count, identity_count + measure_count - 1, 14)
        worksheet.freeze_panes(2, 0)

        workbook.close()
        output.seek(0)
        return output.read()

    def action_export_xlsx(self):
        """Export pipeline summary with two-row headers (primary + secondary)."""
        xlsx_data = self.env['recruitment.pipeline.summary.view']._generate_xlsx_bytes()
        attachment = self.env['ir.attachment'].create({
            'name': 'Pipeline_Summary.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
