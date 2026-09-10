# -*- coding: utf-8 -*-
import base64

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .contract import STATE_LABELS, STATE_SELECTION, TYPE_SELECTION
from .contract_report_xlsx import MSA_COLUMNS, SOW_COLUMNS, build_contract_report_xlsx

# Per-section workbook settings: columns, worksheet name, download filename.
EXPORT_SETTINGS = {
    'msa': (MSA_COLUMNS, 'MSA', 'MSA_Report.xlsx'),
    'sow': (SOW_COLUMNS, 'SOW', 'SOW_Report.xlsx'),
}


class ContractReportWizard(models.TransientModel):
    _name = 'contracts.report.wizard'
    _description = 'Contract Report Export Wizard'

    # ── Contract filters ──────────────────────────────────────────
    contract_type = fields.Selection(
        TYPE_SELECTION, required=True,
    )
    client = fields.Char(
        string='Client',
        help="Partial match. Leave empty to include every client.",
    )
    candidate = fields.Char(
        string='Candidate',
        help="Partial match. Leave empty to include every candidate.",
    )
    role = fields.Char(
        string='Role',
        help="Partial match. Leave empty to include every role.",
    )
    state = fields.Selection(
        STATE_SELECTION, string='Status',
        help="Leave empty to include Active, Expired and Terminated contracts.",
    )
    created_by_ids = fields.Many2many(
        'res.users', string='Created By',
        help="Leave empty to include contracts created by anyone.",
    )

    # ── Date filters ──────────────────────────────────────────────
    start_date_from = fields.Date(string='Start Date From')
    start_date_to = fields.Date(string='Start Date To')
    end_date_from = fields.Date(string='End Date From')
    end_date_to = fields.Date(string='End Date To')
    expiring_within_days = fields.Integer(
        string='Expiring Within (Days)',
        help="Only keep active contracts ending within this many days from today. "
             "Leave at 0 to ignore.",
    )

    # ── Constraints ───────────────────────────────────────────────
    @api.constrains('start_date_from', 'start_date_to', 'end_date_from', 'end_date_to')
    def _check_date_ranges(self):
        for rec in self:
            if rec.start_date_from and rec.start_date_to and rec.start_date_from > rec.start_date_to:
                raise ValidationError(_("'Start Date From' cannot be later than 'Start Date To'."))
            if rec.end_date_from and rec.end_date_to and rec.end_date_from > rec.end_date_to:
                raise ValidationError(_("'End Date From' cannot be later than 'End Date To'."))

    @api.constrains('expiring_within_days')
    def _check_expiring_within_days(self):
        for rec in self:
            if rec.expiring_within_days < 0:
                raise ValidationError(_("'Expiring Within (Days)' cannot be negative."))

    # ── Domain ────────────────────────────────────────────────────
    def _get_domain(self):
        self.ensure_one()
        domain = [('contract_type', '=', self.contract_type)]
        if self.client:
            domain.append(('client', 'ilike', self.client))
        if self.contract_type == 'sow':
            if self.candidate:
                domain.append(('candidate', 'ilike', self.candidate))
            if self.role:
                domain.append(('role', 'ilike', self.role))
        if self.state:
            domain.append(('state', '=', self.state))
        if self.created_by_ids:
            domain.append(('created_by_id', 'in', self.created_by_ids.ids))
        if self.start_date_from:
            domain.append(('start_date', '>=', self.start_date_from))
        if self.start_date_to:
            domain.append(('start_date', '<=', self.start_date_to))
        if self.end_date_from:
            domain.append(('end_date', '>=', self.end_date_from))
        if self.end_date_to:
            domain.append(('end_date', '<=', self.end_date_to))
        if self.expiring_within_days:
            today = fields.Date.context_today(self)
            domain += [
                ('state', '=', 'active'),
                ('end_date', '>=', today),
                ('end_date', '<=', fields.Date.add(today, days=self.expiring_within_days)),
            ]
        return domain

    # ── Filter summary printed in the workbook ────────────────────
    @staticmethod
    def _format_date(value):
        return value.strftime('%d-%b-%Y') if value else _('any')

    def _get_filter_lines(self):
        self.ensure_one()
        lines = []
        if self.client:
            lines.append(_("Client contains: %s", self.client))
        if self.contract_type == 'sow':
            if self.candidate:
                lines.append(_("Candidate contains: %s", self.candidate))
            if self.role:
                lines.append(_("Role contains: %s", self.role))
        if self.state:
            lines.append(_("Status: %s", STATE_LABELS.get(self.state, self.state)))
        if self.created_by_ids:
            lines.append(_("Created By: %s", ', '.join(self.created_by_ids.mapped('name'))))
        if self.start_date_from or self.start_date_to:
            lines.append(_(
                "Start Date: %(start)s to %(end)s",
                start=self._format_date(self.start_date_from),
                end=self._format_date(self.start_date_to),
            ))
        if self.end_date_from or self.end_date_to:
            lines.append(_(
                "End Date: %(start)s to %(end)s",
                start=self._format_date(self.end_date_from),
                end=self._format_date(self.end_date_to),
            ))
        if self.expiring_within_days:
            lines.append(_("Active contracts expiring within %s days", self.expiring_within_days))

        if not lines:
            return [_("No filters applied - all contracts included.")]
        return [_("Filters applied:")] + [f'    - {line}' for line in lines]

    # ── Report data ───────────────────────────────────────────────
    def _get_report_data(self):
        self.ensure_one()
        contracts = self.env['contracts.contract'].search(
            self._get_domain(),
            order='client asc, end_date desc, id asc',
        )

        rows = []
        for seq, contract in enumerate(contracts, start=1):
            attachments = contract._get_documents()
            rows.append({
                'seq': seq,
                'client': contract.client or '',
                'candidate': contract.candidate or '',
                'role': contract.role or '',
                'created_by': contract.created_by_id.name or '',
                'start_date': contract.start_date,
                'end_date': contract.end_date,
                'days_left': contract.days_left,
                'status': STATE_LABELS.get(contract.state, contract.state),
                'termination_date': contract.termination_date,
                'attachment_count': len(attachments),
                'attachments': ', '.join(attachments.mapped('name')),
            })
        return rows

    # ── Export ────────────────────────────────────────────────────
    def action_export_xlsx(self):
        """Export the filtered contracts to Excel."""
        self.ensure_one()
        rows = self._get_report_data()
        generated_on = fields.Datetime.context_timestamp(
            self, fields.Datetime.now()
        ).strftime('%d-%b-%Y %H:%M')

        columns, sheet_name, filename = EXPORT_SETTINGS[self.contract_type]
        xlsx_data = build_contract_report_xlsx(
            rows,
            columns,
            sheet_name,
            _("Contracts Report"),
            filter_lines=self._get_filter_lines(),
            generated_on=generated_on,
        )
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
