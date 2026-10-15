# -*- coding: utf-8 -*-
import base64
import io
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# The six details of a POC, in the sheet's order, as
# (key, field on the opportunity for POC 1, field on crm.lead.poc for the
# rest). POC 1 is CRM's own contact fields relabelled (see crm_lead.py).
POC_FIELDS = [
    ('name', 'contact_name', 'name'),
    ('designation', 'function', 'designation'),
    ('phone', 'phone', 'phone'),
    ('email', 'email_from', 'email'),
    ('location', 'poc1_location', 'location'),
    ('linkedin', 'poc1_linkedin', 'linkedin'),
]

# (column label, row key, width). The order is the sheet's.
EXPORT_COLUMNS = [
    ('Client Name', 'client', 28),
    ('POC Name', 'name', 24),
    ('Designation', 'designation', 24),
    ('Mobile Number', 'phone', 18),
    ('Email', 'email', 30),
    ('Location', 'location', 18),
    ('LinkedIn', 'linkedin', 40),
]


class CrmPocExportWizard(models.TransientModel):
    _name = 'crm.poc.export.wizard'
    _description = 'Export POCs'

    # Picking clients is picking opportunities: the opportunity title is the
    # client's name. Pre-filled with the selection when opened from the list.
    lead_ids = fields.Many2many(
        'crm.lead', string='Clients',
        domain="[('type', '=', 'opportunity')]",
        help='Leave empty to export the POCs of every client matching the '
             'other filters.')
    client_type_ids = fields.Many2many('crm.client.type', string='Client Types')
    industry_domain_ids = fields.Many2many('crm.industry.domain', string='Industries / Domains')
    client_status = fields.Selection(
        [('active', 'Active'), ('inactive', 'Inactive'), ('hold', 'Hold')],
        string='Client Status')
    engagement_type = fields.Selection(
        [('fte', 'FTE'), ('consulting', 'Consulting'), ('fte_consulting', 'FTE/Consulting')],
        string='Engagement Type')
    stage_ids = fields.Many2many('crm.stage', string='Stages')
    bda_ids = fields.Many2many(
        'res.users', string='BDAs', domain="[('share', '=', False)]")
    date_from = fields.Date('Outreach From')
    date_to = fields.Date('Outreach To')
    include_lost = fields.Boolean(
        'Include Lost Opportunities',
        help='Lost opportunities are archived, so they are left out unless '
             'this is ticked.')
    primary_only = fields.Boolean(
        'Primary POC Only',
        help='Export only POC 1 of each client, not the additional POCs.')

    file_data = fields.Binary('File', readonly=True, attachment=False)
    file_name = fields.Char('File Name', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        if 'lead_ids' in fields_list and ctx.get('active_model') == 'crm.lead' and ctx.get('active_ids'):
            res['lead_ids'] = [fields.Command.set(ctx['active_ids'])]
        return res

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(_("'Outreach From' cannot be later than 'Outreach To'."))

    def _get_domain(self):
        self.ensure_one()
        domain = [('type', '=', 'opportunity')]
        if self.include_lost:
            domain.append(('active', 'in', [True, False]))
        if self.lead_ids:
            domain.append(('id', 'in', self.lead_ids.ids))
        if self.client_type_ids:
            domain.append(('client_type', 'in', self.client_type_ids.ids))
        if self.industry_domain_ids:
            domain.append(('industry_domain', 'in', self.industry_domain_ids.ids))
        if self.client_status:
            domain.append(('client_status', '=', self.client_status))
        if self.engagement_type:
            domain.append(('engagement_type', '=', self.engagement_type))
        if self.stage_ids:
            domain.append(('stage_id', 'in', self.stage_ids.ids))
        if self.bda_ids:
            domain.append(('bda_ids', 'in', self.bda_ids.ids))
        if self.date_from:
            domain.append(('initial_outreach_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('initial_outreach_date', '<=', self.date_to))
        return domain

    def _get_rows(self):
        """One row per POC that holds anything, client by client: POC 1,
        then every additional POC in the order set on the form.

        Searched as the user, so CRM's record rules decide whose clients a
        salesperson can export, the same as in the pipeline.
        """
        self.ensure_one()
        leads = self.env['crm.lead'].search(self._get_domain(), order='name, id')
        rows = []
        for lead in leads:
            pocs = [{key: lead[lead_field] for key, lead_field, _poc_field in POC_FIELDS}]
            if not self.primary_only:
                pocs += [{key: poc[poc_field] for key, _lead_field, poc_field in POC_FIELDS}
                         for poc in lead.poc_ids]
            for poc in pocs:
                values = {key: (value or '').strip() for key, value in poc.items()}
                if any(values.values()):
                    rows.append(dict(values, client=lead.name or ''))
        return rows

    @staticmethod
    def _build_xlsx(rows):
        import xlsxwriter  # noqa: PLC0415

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('POCs')
        header_fmt = workbook.add_format({
            'bold': True, 'valign': 'vcenter', 'font_color': '#FFFFFF',
            'bg_color': '#1A3A5C', 'border': 1, 'text_wrap': True,
        })
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        link_fmt = workbook.add_format({
            'border': 1, 'valign': 'vcenter', 'font_color': '#0563C1', 'underline': 1,
        })

        sheet.set_row(0, 22)
        for col, (label, _key, width) in enumerate(EXPORT_COLUMNS):
            sheet.write_string(0, col, label, header_fmt)
            sheet.set_column(col, col, width)
        sheet.freeze_panes(1, 0)

        for row_idx, row in enumerate(rows, start=1):
            for col, (_label, key, _width) in enumerate(EXPORT_COLUMNS):
                value = row[key]
                # Strings throughout, so a mobile number keeps its leading
                # + or 0 instead of turning into a number. Only a well-formed
                # web address is made clickable; anything else is kept as typed.
                if key == 'linkedin' and re.match(r'^https?://\S+$', value) and len(value) <= 2079:
                    sheet.write_url(row_idx, col, value, link_fmt, string=value)
                else:
                    sheet.write_string(row_idx, col, value, cell_fmt)

        sheet.autofilter(0, 0, max(len(rows), 1), len(EXPORT_COLUMNS) - 1)
        workbook.close()
        return output.getvalue()

    def action_export_xlsx(self):
        self.ensure_one()
        rows = self._get_rows()
        if not rows:
            raise UserError(_('No POCs match these filters.'))
        self.write({
            'file_data': base64.b64encode(self._build_xlsx(rows)),
            'file_name': 'POCs_%s.xlsx' % fields.Date.context_today(self).strftime('%Y-%m-%d'),
        })
        # Served off the wizard itself rather than a stand-alone attachment,
        # so the file is cleaned up with the wizard instead of piling up.
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/file_data/%s?download=true' % (
                self._name, self.id, self.file_name),
            'target': 'self',
        }
