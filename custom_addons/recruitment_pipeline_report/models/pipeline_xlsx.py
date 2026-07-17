# -*- coding: utf-8 -*-
import io

from .pipeline_constants import PRIMARY_HEADERS


def build_pipeline_xlsx(rows, stages):
    """Build pipeline summary XLSX with two-row headers from wizard row dicts."""
    import xlsxwriter  # noqa: PLC0415

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
    measure_count = len(stages)

    for col, title in enumerate(PRIMARY_HEADERS):
        worksheet.write(0, col, title, primary_fmt)
        worksheet.write(1, col, '', secondary_fmt)

    if measure_count > 0:
        worksheet.merge_range(
            0, identity_count, 0, identity_count + measure_count - 1,
            'Pipeline Summary', pipeline_hdr_fmt,
        )
        for col, title in enumerate(stages, start=identity_count):
            worksheet.write(1, col, title, secondary_fmt)

    for row_idx, row in enumerate(rows, start=2):
        identity_values = [
            row.get('seq', row_idx - 1),
            row.get('client', ''),
            row.get('poc', ''),
            row.get('role', ''),
            row.get('role_type', ''),
            row.get('role_status', ''),
            row.get('sub_status', ''),
            row.get('role_received_date', ''),
            row.get('role_opened_date', ''),
            row.get('no_of_positions', 0),
        ]
        for col, val in enumerate(identity_values):
            fmt = num_fmt if col in (0, identity_count - 1) else cell_fmt
            worksheet.write(row_idx, col, val, fmt)
            
        stage_counts = row.get('stage_counts', {})
        for col, stage_name in enumerate(stages, start=identity_count):
            worksheet.write(row_idx, col, stage_counts.get(stage_name, 0), num_fmt)

    worksheet.set_column(0, 0, 4)
    worksheet.set_column(1, 3, 18)
    worksheet.set_column(4, 9, 12)
    worksheet.set_column(identity_count, identity_count + measure_count - 1, 14)
    worksheet.freeze_panes(2, 0)

    workbook.close()
    output.seek(0)
    return output.read()
