# -*- coding: utf-8 -*-
import io

# (column label, row key, width). The order is the sheet's. Each report leads
# with the client and what it measures, then the same account details.
_ACCOUNT_COLUMNS = [
    ('BDAs', 'bdas', 26),
    ('Client Type', 'client_type', 16),
    ('Industry / Domain', 'industry', 20),
    ('Engagement Type', 'engagement_type', 16),
    ('POC Name', 'poc', 22),
    ('POC Phone', 'poc_phone', 16),
    ('POC Email', 'poc_email', 28),
    ('Next Activity', 'next_activity', 34),
    ('Start Date', 'start_date', 15),
    ('End Date', 'end_date', 15),
    ('Link', 'url', 10),
]

STAGE_AGEING_COLUMNS = [
    ('Client Name', 'client', 28),
    ('Current Stage', 'stage', 22),
    ('In Stage Since', 'since', 15),
    ('Days in Stage', 'days', 12),
] + _ACCOUNT_COLUMNS

INACTIVITY_COLUMNS = [
    ('Client Name', 'client', 28),
    ('Current Stage', 'stage', 22),
    ('Last Activity', 'since', 15),
    ('Days Inactive', 'days', 12),
] + _ACCOUNT_COLUMNS


def build_pipeline_report_xlsx(rows, columns, sheet_name, title, subtitle, min_days):
    """A pipeline report as an Excel workbook, one row per client.

    The day count ('days') is a number, so the sheet sorts and filters on it;
    it is shaded red once a client has reached twice the threshold.
    """
    import xlsxwriter  # noqa: PLC0415

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet = workbook.add_worksheet(sheet_name)
    last_col = len(columns) - 1

    title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#1A3A5C'})
    subtitle_fmt = workbook.add_format({'italic': True, 'font_color': '#666666'})
    header_fmt = workbook.add_format({
        'bold': True, 'valign': 'vcenter', 'font_color': '#FFFFFF',
        'bg_color': '#1A3A5C', 'border': 1, 'text_wrap': True,
    })
    cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
    days_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center', 'bold': True,
        'bg_color': '#FDEBD0', 'font_color': '#9C640C',
    })
    days_long_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center', 'bold': True,
        'bg_color': '#FADBD8', 'font_color': '#922B21',
    })
    link_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'font_color': '#0563C1', 'underline': 1,
    })
    muted_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'italic': True, 'font_color': '#999999',
    })

    sheet.write_string(0, 0, title, title_fmt)
    sheet.write_string(1, 0, subtitle, subtitle_fmt)

    header_row = 3
    sheet.set_row(header_row, 22)
    for col, (label, _key, width) in enumerate(columns):
        sheet.write_string(header_row, col, label, header_fmt)
        sheet.set_column(col, col, width)
    sheet.freeze_panes(header_row + 1, 1)

    for row_idx, row in enumerate(rows, start=header_row + 1):
        for col, (_label, key, _width) in enumerate(columns):
            value = row[key]
            if key == 'days':
                sheet.write_number(row_idx, col, value,
                                   days_long_fmt if value >= 2 * min_days else days_fmt)
            elif key == 'url':
                sheet.write_url(row_idx, col, value, link_fmt, string='Open')
            elif key == 'next_activity' and not value:
                sheet.write_string(row_idx, col, 'None scheduled', muted_fmt)
            else:
                # Strings throughout, so a phone number keeps its leading + or 0.
                sheet.write_string(row_idx, col, value or '', cell_fmt)

    if rows:
        sheet.autofilter(header_row, 0, header_row + len(rows), last_col)
    workbook.close()
    return output.getvalue()
