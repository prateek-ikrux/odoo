# -*- coding: utf-8 -*-
import io

# ── Column definitions ────────────────────────────────────────────────────────
# Each entry: (column_label, data_key, col_width, kind)
# kind drives the cell format: 'text' | 'date' | 'int' | 'status' | 'days_left'

CONTRACT_COLUMNS = [
    ('Client',           'client',           24, 'text'),
    ('Role',             'role',             26, 'text'),
    ('Created By',       'created_by',       20, 'text'),
    ('Start Date',       'start_date',       14, 'date'),
    ('End Date',         'end_date',         14, 'date'),
    ('Days Left',        'days_left',        11, 'days_left'),
    ('Status',           'status',           14, 'status'),
    ('Termination Date', 'termination_date', 16, 'date'),
    ('# Attachments',    'attachment_count', 13, 'int'),
    ('Attachments',      'attachments',      40, 'text'),
]

HEADER_BG = '#1A3A5C'
TITLE_BG = '#2C3E50'


def build_contract_report_xlsx(rows, filter_lines=None, generated_on=''):
    """Build the Contracts XLSX.

    :param rows: list of dicts keyed by the data keys in ``CONTRACT_COLUMNS``.
    :param filter_lines: list of "Label: value" strings describing the filters
        the user applied, printed under the title.
    :param generated_on: formatted timestamp shown in the title block.
    :return: the workbook as bytes.
    """
    import xlsxwriter  # noqa: PLC0415

    filter_lines = filter_lines or ['No filters applied - all contracts included.']
    last_col = len(CONTRACT_COLUMNS)  # col 0 is the sequence column

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Contracts')

    # ── Formats ───────────────────────────────────────────────────────────────
    title_fmt = workbook.add_format({
        'bold': True, 'font_size': 15, 'align': 'left', 'valign': 'vcenter',
        'bg_color': TITLE_BG, 'font_color': '#FFFFFF',
    })
    subtitle_fmt = workbook.add_format({
        'font_size': 9, 'italic': True, 'align': 'left', 'valign': 'vcenter',
        'font_color': '#5D6D7E',
    })
    filter_fmt = workbook.add_format({
        'font_size': 9, 'align': 'left', 'valign': 'vcenter',
        'font_color': '#34495E',
    })
    hdr_fmt = workbook.add_format({
        'bold': True, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
        'bg_color': HEADER_BG, 'font_color': '#FFFFFF', 'border': 1,
    })
    seq_fmt = workbook.add_format({
        'align': 'center', 'valign': 'vcenter', 'border': 1,
        'bg_color': '#F0F3F4', 'font_color': '#2C3E50',
    })
    cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'text_wrap': True})
    date_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center', 'num_format': 'dd-mmm-yyyy',
    })
    int_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center'})
    na_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'font_color': '#999999', 'italic': True,
    })
    total_fmt = workbook.add_format({
        'bold': True, 'align': 'left', 'valign': 'vcenter', 'font_color': '#2C3E50',
    })

    status_fmts = {
        'Active': workbook.add_format({
            'border': 1, 'valign': 'vcenter', 'align': 'center', 'bold': True,
            'bg_color': '#D5F5E3', 'font_color': '#1E8449',
        }),
        'Expired': workbook.add_format({
            'border': 1, 'valign': 'vcenter', 'align': 'center', 'bold': True,
            'bg_color': '#FDEBD0', 'font_color': '#9C640C',
        }),
        'Terminated': workbook.add_format({
            'border': 1, 'valign': 'vcenter', 'align': 'center', 'bold': True,
            'bg_color': '#FDECEA', 'font_color': '#922B21',
        }),
    }
    days_urgent_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center', 'bold': True,
        'bg_color': '#FDECEA', 'font_color': '#922B21',
    })
    days_soon_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'bg_color': '#FEF9E7', 'font_color': '#9C640C',
    })

    # ── Title block ───────────────────────────────────────────────────────────
    worksheet.merge_range(0, 0, 0, last_col, '  Contracts Report', title_fmt)
    worksheet.set_row(0, 28)
    worksheet.merge_range(
        1, 0, 1, last_col,
        f'  Generated on {generated_on}' if generated_on else '',
        subtitle_fmt,
    )

    row_idx = 2
    for line in filter_lines:
        worksheet.merge_range(row_idx, 0, row_idx, last_col, f'  {line}', filter_fmt)
        row_idx += 1
    row_idx += 1  # spacer row

    # ── Header row ────────────────────────────────────────────────────────────
    header_row = row_idx
    worksheet.write(header_row, 0, '#', hdr_fmt)
    for i, (label, key, width, kind) in enumerate(CONTRACT_COLUMNS):
        worksheet.write(header_row, i + 1, label, hdr_fmt)
    worksheet.set_row(header_row, 28)

    # ── Column widths ─────────────────────────────────────────────────────────
    worksheet.set_column(0, 0, 5)
    for i, (label, key, width, kind) in enumerate(CONTRACT_COLUMNS):
        worksheet.set_column(i + 1, i + 1, width)

    worksheet.freeze_panes(header_row + 1, 0)

    # ── Data rows ─────────────────────────────────────────────────────────────
    for offset, row in enumerate(rows):
        r = header_row + 1 + offset
        worksheet.write(r, 0, row.get('seq', offset + 1), seq_fmt)

        for i, (label, key, width, kind) in enumerate(CONTRACT_COLUMNS):
            col = i + 1
            val = row.get(key)

            if kind == 'date':
                if val:
                    worksheet.write_datetime(r, col, val, date_fmt)
                else:
                    worksheet.write(r, col, 'N/A', na_fmt)
            elif kind == 'status':
                worksheet.write(r, col, val or '', status_fmts.get(val, cell_fmt))
            elif kind == 'days_left':
                days = val or 0
                if row.get('status') != 'Active':
                    worksheet.write(r, col, 'N/A', na_fmt)
                elif days <= 7:
                    worksheet.write_number(r, col, days, days_urgent_fmt)
                elif days <= 30:
                    worksheet.write_number(r, col, days, days_soon_fmt)
                else:
                    worksheet.write_number(r, col, days, int_fmt)
            elif kind == 'int':
                worksheet.write_number(r, col, val or 0, int_fmt)
            else:
                worksheet.write(r, col, val or '', cell_fmt)

    # ── Autofilter + total ────────────────────────────────────────────────────
    if rows:
        worksheet.autofilter(header_row, 0, header_row + len(rows), last_col)
        total_row = header_row + len(rows) + 2
    else:
        worksheet.merge_range(
            header_row + 1, 0, header_row + 1, last_col,
            'No contracts matched the selected filters.', na_fmt,
        )
        total_row = header_row + 3

    worksheet.merge_range(
        total_row, 0, total_row, last_col,
        f'Total contracts: {len(rows)}', total_fmt,
    )

    workbook.close()
    output.seek(0)
    return output.read()
