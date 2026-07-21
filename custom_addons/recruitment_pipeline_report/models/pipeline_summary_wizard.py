# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from collections import defaultdict

from .pipeline_constants import (
    ROLE_STATUS_LABELS,
    SUB_STATUS_LABELS,
    SUB_STATUS_SELECTION,
    EMP_TYPE_LABELS,
    DATE_FILTER_TYPE_SELECTION,
    build_date_range_domain,
)
from .stage_history import (
    as_of_utc_datetime,
    day_start_utc,
    get_applicants_moved_between,
    get_stage_as_of,
)
from .pipeline_xlsx import build_pipeline_xlsx


class PipelineSummaryWizard(models.TransientModel):
    _name = 'recruitment.pipeline.summary.wizard'
    _description = 'Pipeline Summary Report Wizard'

    # ── Date Range ────────────────────────────────────────────────
    date_filter_type = fields.Selection(
        DATE_FILTER_TYPE_SELECTION,
        string='Filter By',
        default='create_date',
        required=True,
        help="Profile Created Date filters by when the candidate was added to the "
             "system.\nLast Stage Activity Date includes every candidate who had "
             "a stage change at any point within the selected range - even if "
             "they were added earlier, and even if they've moved again since - "
             "showing each one's stage as it stood at the end of the range.",
    )
    date_from      = fields.Date(string='Date From')
    date_to        = fields.Date(string='Date To')

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError("'Date From' cannot be later than 'Date To'.")

    # ── Role Filters ──────────────────────────────────────────────
    department_ids = fields.Many2many('hr.department', string='Clients')
    job_ids        = fields.Many2many('hr.job',        string='Roles')
    job_ids_domain = fields.Binary(compute='_compute_job_ids_domain')
    poc_ids        = fields.Many2many('res.partner',   string='POC')
    poc_ids_domain = fields.Binary(compute='_compute_poc_ids_domain')
    role_status    = fields.Selection(
        ROLE_STATUS_LABELS.items(),
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

    # ── Candidate / Pipeline Filters ──────────────────────────────
    recruiter_ids  = fields.Many2many('res.users', string='Recruiters')
    stage_ids      = fields.Many2many('hr.recruitment.stage', string='Stages')

    # ── Dynamic domains ──────────────────────────────────────────
    @api.depends('department_ids')
    def _compute_job_ids_domain(self):
        for rec in self:
            if rec.department_ids:
                rec.job_ids_domain = [('department_id', 'in', rec.department_ids.ids)]
            else:
                rec.job_ids_domain = []

    @api.depends('department_ids')
    def _compute_poc_ids_domain(self):
        for rec in self:
            if rec.department_ids:
                rec.poc_ids_domain = [('x_client_department_id', 'in', rec.department_ids.ids)]
            else:
                rec.poc_ids_domain = [('x_client_department_id', '!=', False)]

    def _base_domain(self):
        domain = [('active', 'in', [True, False])]
        if self.date_filter_type == 'date_last_stage_update':
            # This reconstructs history rather than filtering by a stored
            # field, so only candidates that already existed by the end of
            # the range are in scope here; the actual "did they move in this
            # window" check happens in _get_report_data. The live stage_id
            # filter below is skipped here too and re-applied against the
            # reconstructed stage.
            domain.append(('create_date', '<=', as_of_utc_datetime(self.env, self.date_to)))
        else:
            domain += build_date_range_domain(
                self.env, self.date_from, self.date_to,
                self.date_filter_type or 'create_date',
            )
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        if self.job_ids:
            domain.append(('job_id', 'in', self.job_ids.ids))
        if self.poc_ids:
            domain.append(('job_id.x_poc_id', 'in', self.poc_ids.ids))
        if self.role_status:
            domain.append(('job_id.x_role_status', '=', self.role_status))
        if self.sub_status:
            domain.append(('job_id.x_sub_status', '=', self.sub_status))
        if self.employment_type:
            domain.append(('job_id.x_employment_type', '=', self.employment_type))
        if self.recruiter_ids:
            domain.append(('user_id', 'in', self.recruiter_ids.ids))
        if self.stage_ids and self.date_filter_type != 'date_last_stage_update':
            domain.append(('stage_id', 'in', self.stage_ids.ids))
        return domain

    def _get_report_data(self):
        stages = self.env['hr.recruitment.stage'].search([], order='sequence')
        stage_names = [s.name for s in stages]
        applicants = self.env['hr.applicant'].search(self._base_domain())

        is_last_activity = self.date_filter_type == 'date_last_stage_update'
        stage_as_of = {}

        if is_last_activity:
            end = as_of_utc_datetime(self.env, self.date_to)
            start = day_start_utc(self.env, self.date_from)
            moved_ids = get_applicants_moved_between(self.env, start, end, applicants.ids)
            applicants = applicants.filtered(lambda a: a.id in moved_ids)
            # Stage as of the end of the range - correctly reflects only the
            # in-range move(s), ignoring anything that happened afterwards.
            stage_as_of = get_stage_as_of(self.env, end, applicants.ids)
            if self.stage_ids:
                wanted = set(self.stage_ids.ids)
                applicants = applicants.filtered(lambda a: stage_as_of.get(a.id) in wanted)

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
            role_received_date = job.x_role_received_date if job else False
            role_opened_date   = job.x_role_opened_date   if job else False
            def count_stage(stage_id):
                if is_last_activity:
                    return sum(1 for a in apps if stage_as_of.get(a.id) == stage_id)
                return sum(1 for a in apps if a.stage_id.id == stage_id)

            row = {
                'seq':                 seq,
                'client':              dept.name if dept else '-',
                'poc':                 poc.name  if poc  else '-',
                'role':                job.name  if job  else '-',
                'role_type':           EMP_TYPE_LABELS.get(emp_type, emp_type),
                'role_type_key':       emp_type,
                'role_status':         ROLE_STATUS_LABELS.get(role_status, role_status),
                'role_status_key':     role_status,
                'sub_status':          SUB_STATUS_LABELS.get(sub_status, sub_status or ''),
                'role_received_date':  role_received_date.strftime('%d-%b-%Y') if role_received_date else '',
                'role_opened_date':    role_opened_date.strftime('%d-%b-%Y')   if role_opened_date   else '',
                'no_of_positions':     no_of_pos,
                'stage_counts':        {},
            }
            for s in stages:
                row['stage_counts'][s.name] = count_stage(s.id)
            rows.append(row)
            seq += 1

        return rows, stage_names

    def action_print_report(self):
        return self.env.ref(
            'recruitment_pipeline_report.action_report_pipeline_summary'
        ).report_action(self)

    def action_export_xlsx(self):
        """Export filtered pipeline summary to Excel with two-row headers."""
        rows, stages = self._get_report_data()
        xlsx_data = build_pipeline_xlsx(rows, stages)
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
