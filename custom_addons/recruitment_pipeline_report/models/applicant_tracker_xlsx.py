# -*- coding: utf-8 -*-
import io


# ── Column definitions ────────────────────────────────────────────────────────
# Each entry: (section_label, column_label, data_key, col_width)
# section_label='' means the column falls under the previous section merge.

TRACKER_COLUMNS = [
    # ── Requisition Details ──────────────────────────────────────
    ('Requisition Details',  'Req ID',               'req_id',                 12),
    ('',                     'Client Name',           'client',                 18),
    ('',                     'Position / Role Name',  'role',                   22),
    ('',                     'Role Type',             'role_type',              12),
    ('',                     'TE / Recruiter',        'recruiter',              18),

    # ── Application Details ──────────────────────────────────────
    ('Application Details',  'Source',                'source',                 14),
    ('',                     'Application Date',      'application_date',       14),
    ('',                     'Current Status',        'current_status',         18),
    ('',                     'Client Portal Status',  'client_portal_status',   16),

    # ── Candidate Details ────────────────────────────────────────
    ('Candidate Details',    'Candidate Name',        'candidate_name',         20),
    ('',                     'Contact Number',      'candidate_number',       16),
    ('',                     'Email ID',    'candidate_email',        24),
    ('',                     'Skill',                 'skill',                  18),
    ('',                     'Total Experience',      'total_experience',       14),
    ('',                     'Relevant Experience',   'relevant_experience',    16),
    ('',                     'Current Organization',  'current_organization',   22),
    ('',                     'Designation',           'designation',            18),
    ('',                     'Education',             'education',              18),

    # ── Location & Availability ──────────────────────────────────
    ('Location & Availability', 'Current Location',  'current_location',       18),
    ('',                        'Preferred Location', 'preferred_location',     18),
    ('',                        'Notice Period',      'notice_period',          14),
    ('',                        'Last Working Date',                'lwd',                    14),

    # ── Compensation ─────────────────────────────────────────────
    ('Compensation',         'Current CTC (LPA)',     'current_ctc',            14),
    ('',                     'Expected CTC (LPA)',    'expected_ctc',           14),
    ('',                     'Budget (LPA)',          'budget',                 14),
    ('',                     'Bill Rate (LPM)',       'bill_rate',              14),
    ('',                     'Offer in Hand (LPA)',   'offer_in_hand',          14),

    # ── Additional Information ───────────────────────────────────
    ('Additional Information', 'Reason for Job Change', 'reason_for_job_change', 28),
    ('',                       'Remarks',               'remarks',               28),
]

# ── Section colour map ────────────────────────────────────────────────────────
SECTION_COLOURS = {
    'Requisition Details':    '#1A3A5C',
    'Application Details':    '#1A6B4A',
    'Candidate Details':      '#6B3A1A',
    'Location & Availability':'#4A1A6B',
    'Compensation':           '#1A5C6B',
    'Additional Information': '#5C1A1A',
}


def build_tracker_xlsx(rows):
    """Build Applicant Tracker XLSX with two-row grouped headers."""
    import xlsxwriter  # noqa: PLC0415

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Applicant Tracker')

    # ── Base formats ──────────────────────────────────────────────────────────
    base_section = {
        'bold': True, 'align': 'center', 'valign': 'vcenter',
        'font_color': '#FFFFFF', 'border': 1, 'text_wrap': True,
    }
    col_hdr_fmt = workbook.add_format({
        'bold': True, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#F0F3F4', 'border': 1, 'text_wrap': True,
    })
    seq_fmt = workbook.add_format({
        'bold': True, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#2C3E50', 'font_color': '#FFFFFF', 'border': 1,
    })
    cell_fmt  = workbook.add_format({'border': 1, 'valign': 'vcenter', 'text_wrap': True})
    na_fmt    = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'font_color': '#999999', 'italic': True,
    })
    portal_uploaded_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'bg_color': '#D5F5E3', 'font_color': '#1E8449',
    })
    portal_pending_fmt = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'bg_color': '#FDECEA', 'font_color': '#922B21',
    })

    # Cache section formats by colour
    _section_fmts = {}
    def section_fmt(colour):
        if colour not in _section_fmts:
            _section_fmts[colour] = workbook.add_format({**base_section, 'bg_color': colour})
        return _section_fmts[colour]

    # ── Write # header (row 0 + row 1, merged) ───────────────────────────────
    worksheet.merge_range(0, 0, 1, 0, '#', seq_fmt)

    # ── Build section spans ───────────────────────────────────────────────────
    # col 0 = # (seq), TRACKER_COLUMNS start at col 1
    sections = []   # (section_label, start_col, end_col)
    current_section = None
    current_start   = None

    for i, (sec, col_lbl, key, width) in enumerate(TRACKER_COLUMNS):
        col = i + 1  # offset by 1 for the # column
        if sec:
            if current_section is not None:
                sections.append((current_section, current_start, col - 1))
            current_section = sec
            current_start   = col
    if current_section is not None:
        sections.append((current_section, current_start, len(TRACKER_COLUMNS)))

    # ── Row 0: section headers (merged) ──────────────────────────────────────
    for sec_label, sc, ec in sections:
        colour = SECTION_COLOURS.get(sec_label, '#2C3E50')
        fmt    = section_fmt(colour)
        if sc == ec:
            worksheet.write(0, sc, sec_label, fmt)
        else:
            worksheet.merge_range(0, sc, 0, ec, sec_label, fmt)

    # ── Row 1: column sub-headers ─────────────────────────────────────────────
    for i, (sec, col_lbl, key, width) in enumerate(TRACKER_COLUMNS):
        worksheet.write(1, i + 1, col_lbl, col_hdr_fmt)

    # ── Column widths ─────────────────────────────────────────────────────────
    worksheet.set_column(0, 0, 4)           # #
    for i, (sec, col_lbl, key, width) in enumerate(TRACKER_COLUMNS):
        worksheet.set_column(i + 1, i + 1, width)

    # ── Freeze header rows ────────────────────────────────────────────────────
    worksheet.freeze_panes(2, 0)

    # ── Data rows ─────────────────────────────────────────────────────────────
    for row_idx, row in enumerate(rows, start=2):
        worksheet.write(row_idx, 0, row.get('seq', row_idx - 1), seq_fmt)

        for i, (sec, col_lbl, key, width) in enumerate(TRACKER_COLUMNS):
            col = i + 1
            val = row.get(key, '')

            # N/A cells get muted italic style
            if val == 'N/A':
                worksheet.write(row_idx, col, val, na_fmt)
            # Client Portal Status – colour coded
            elif key == 'client_portal_status':
                fmt = portal_uploaded_fmt if val == 'Uploaded' else portal_pending_fmt
                worksheet.write(row_idx, col, val, fmt)
            else:
                worksheet.write(row_idx, col, val, cell_fmt)

    # ── Row height for header rows ────────────────────────────────────────────
    worksheet.set_row(0, 22)
    worksheet.set_row(1, 30)

    workbook.close()
    output.seek(0)
    return output.read()
