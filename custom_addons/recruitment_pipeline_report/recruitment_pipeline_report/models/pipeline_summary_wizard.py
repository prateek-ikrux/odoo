# -*- coding: utf-8 -*-
import base64

from odoo import models, fields
from collections import defaultdict

from .pipeline_constants import (
    ROLE_STATUS_LABELS,
    SUB_STATUS_LABELS,
    EMP_TYPE_LABELS,
    STAGE_BY_FIELD,
    MEASURE_FIELDS,
    ALL_STAGE_NAMES,
)
from .pipeline_xlsx import build_pipeline_xlsx


class PipelineSummaryWizard(models.TransientModel):
    _name = 'recruitment.pipeline.summary.wizard'
    _description = 'Pipeline Summary Report Wizard'

    date_from      = fields.Date(string='Date From')
    date_to        = fields.Date(string='Date To')
    department_ids = fields.Many2many('hr.department', string='Clients')
    job_ids        = fields.Many2many('hr.job',        string='Roles')

    def _build_stage_map(self):
        stages = self.env['hr.recruitment.stage'].search([('name', 'in', ALL_STAGE_NAMES)])
        return {s.name: s.id for s in stages}

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
        return domain

    def _get_report_data(self):
        stage_map = self._build_stage_map()
        applicants = self.env['hr.applicant'].search(self._base_domain())

        groups = defaultdict(list)
        for app in applicants:
            key = (
                app.department_id.id if app.department_id else False,
                app.job_id.id        if app.job_id        else False,
            )
            groups[key].append(app)

        rows = []
        seq  = 1

        def sort_key(item):
            (dept_id, job_id), _ = item
            dept = self.env['hr.department'].browse(dept_id) if dept_id else None
            job  = self.env['hr.job'].browse(job_id)         if job_id  else None
            return (dept.name if dept else '', job.name if job else '')

        for (dept_id, job_id), apps in sorted(groups.items(), key=sort_key):
            dept = self.env['hr.department'].browse(dept_id) if dept_id else None
            job  = self.env['hr.job'].browse(job_id)         if job_id  else None

            poc         = job.x_poc_id     if job and job.x_poc_id     else None
            emp_type    = job.x_employment_type if job else 'fte'
            no_of_pos   = job.no_of_recruitment if job else 0
            role_status = job.x_role_status if job else 'active'
            sub_status  = job.x_sub_status if job else False
            def count_field(field_key):
                stage_name = STAGE_BY_FIELD[field_key]
                sid = stage_map.get(stage_name, -1)
                return sum(1 for a in apps if a.stage_id.id == sid)

            row = {
                'seq':             seq,
                'client':          dept.name if dept else '-',
                'poc':             poc.name  if poc  else '-',
                'role':            job.name  if job  else '-',
                'role_type':       EMP_TYPE_LABELS.get(emp_type, emp_type),
                'role_type_key':   emp_type,
                'role_status':     ROLE_STATUS_LABELS.get(role_status, role_status),
                'role_status_key': role_status,
                'sub_status':      SUB_STATUS_LABELS.get(sub_status, sub_status or ''),
                'no_of_positions': no_of_pos,
            }
            for field_key in MEASURE_FIELDS:
                row[field_key] = count_field(field_key)
            rows.append(row)
            seq += 1

        return rows

    def action_print_report(self):
        return self.env.ref(
            'recruitment_pipeline_report.action_report_pipeline_summary'
        ).report_action(self)

    def action_export_xlsx(self):
        """Export filtered pipeline summary to Excel with two-row headers."""
        rows = self._get_report_data()
        xlsx_data = build_pipeline_xlsx(rows)
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
