# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def migrate(cr, version):
    """Backfill the new x_req_id_available radio field on existing Job
    Positions, and the fixed 'iKrux Engineering' Source on existing
    applicants, so the upgrade doesn't disrupt or leave inconsistent data
    on records created before these changes existed."""
    if _column_exists(cr, 'hr_job', 'x_req_id_available'):
        cr.execute("""
            UPDATE hr_job
            SET x_req_id_available = 'yes'
            WHERE x_req_id_available IS NULL
        """)
        _logger.info('Backfilled x_req_id_available = \'yes\' on %s existing job position(s).', cr.rowcount)

    if _column_exists(cr, 'hr_applicant', 'source_id'):
        cr.execute("""
            SELECT res_id FROM ir_model_data
            WHERE module = 'recruitment_pipeline_report'
              AND name = 'utm_source_ikrux_engineering'
              AND model = 'utm.source'
        """)
        row = cr.fetchone()
        if row:
            source_id = row[0]
            cr.execute("""
                UPDATE hr_applicant
                SET source_id = %s
                WHERE source_id IS DISTINCT FROM %s
            """, (source_id, source_id))
            _logger.info('Backfilled source_id = iKrux Engineering on %s existing applicant(s).', cr.rowcount)
        else:
            _logger.warning(
                'Could not find the "iKrux Engineering" utm.source record during '
                'migration; existing applicants were not updated. They will be '
                'corrected automatically the next time each record is saved.'
            )
