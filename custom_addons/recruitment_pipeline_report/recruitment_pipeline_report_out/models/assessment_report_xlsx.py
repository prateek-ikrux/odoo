# -*- coding: utf-8 -*-
import io


# Column definitions: (header_label, data_key, col_width)
ASSESSMENT_COLUMNS = [
    ('Req ID',                    'req_id',                   14),
    ('Client',                    'client',                   18),
    ('Role',                      'role',                     22),
    ('Role Type',                 'role_type',                12),
    ('Role Status',               'role_status',              14),
    ('Role Status Remarks',                'sub_status',               18),
    ('Candidate Name',            'candidate_name',           22),
    ('Assessment Link Received',  'assessment_link_received', 20),
    ('Assessment Taken',          'assessment_taken',         16),
    ('Assessment Feedback',       'assessment_feedback',      18),
    ('Current Hiring Status',     'current_hiring_status',    22),
]


def build_assessment_xlsx(rows):
    """Build Internal Assessment Report XLSX with styled single-row headers."""
    import xlsxwriter  # noqa: PLC0415

    output   = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    ws       = workbook.add_worksheet('Assessment Report')

    # ── Formats ───────────────────────────────────────────────────
    seq_hdr_fmt = workbook.add_format({
        'bold': True, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#2C3E50', 'font_color': '#FFFFFF', 'border': 1,
    })
    hdr_fmt = workbook.add_format({
        'bold': True, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#1A6B9A', 'font_color': '#FFFFFF',
        'border': 1, 'text_wrap': True,
    })
    cell_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'text_wrap': True,
    })
    na_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'font_color': '#999999', 'italic': True,
    })
    yes_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'bg_color': '#D5F5E3', 'font_color': '#1E8449',
    })
    no_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'bg_color': '#FDECEA', 'font_color': '#922B21',
    })
    select_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'bg_color': '#D5F5E3', 'font_color': '#1E8449', 'bold': True,
    })
    reject_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'bg_color': '#FDECEA', 'font_color': '#922B21', 'bold': True,
    })
    seq_fmt = workbook.add_format({
        'border': 1, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#F0F3F4',
    })

    # ── Header row ────────────────────────────────────────────────
    ws.write(0, 0, '#', seq_hdr_fmt)
    for col, (label, key, width) in enumerate(ASSESSMENT_COLUMNS, start=1):
        ws.write(0, col, label, hdr_fmt)

    # ── Column widths ─────────────────────────────────────────────
    ws.set_column(0, 0, 4)
    for col, (label, key, width) in enumerate(ASSESSMENT_COLUMNS, start=1):
        ws.set_column(col, col, width)

    ws.freeze_panes(1, 0)
    ws.set_row(0, 30)

    # ── Data rows ─────────────────────────────────────────────────
    for row_idx, row in enumerate(rows, start=1):
        ws.write(row_idx, 0, row.get('seq', row_idx), seq_fmt)

        for col, (label, key, width) in enumerate(ASSESSMENT_COLUMNS, start=1):
            val = row.get(key, '')

            if val == 'N/A':
                ws.write(row_idx, col, val, na_fmt)
            elif key == 'assessment_link_received':
                ws.write(row_idx, col, val, yes_fmt if val == 'Yes' else no_fmt)
            elif key == 'assessment_taken':
                ws.write(row_idx, col, val, yes_fmt if val == 'Yes' else no_fmt)
            elif key == 'assessment_feedback':
                if val == 'Select':
                    ws.write(row_idx, col, val, select_fmt)
                elif val == 'Reject':
                    ws.write(row_idx, col, val, reject_fmt)
                else:
                    ws.write(row_idx, col, val, cell_fmt)
            else:
                ws.write(row_idx, col, val, cell_fmt)

    workbook.close()
    output.seek(0)
    return output.read()
