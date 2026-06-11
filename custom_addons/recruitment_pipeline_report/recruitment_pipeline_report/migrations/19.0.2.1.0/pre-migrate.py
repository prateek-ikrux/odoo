# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

_SUB_STATUS_MAP = {
    'candidate drop': 'candidate_drop',
    'drop by client': 'drop_by_client',
    'on hold due to alignment': 'on_hold_alignment',
    'nil': 'nil',
    'nil/not applicable': 'nil',
    'n/a': 'nil',
    'not applicable': 'nil',
}


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def migrate(cr, version):
    """Move role/sub status from applicants to job positions before field refactor."""
    if not _column_exists(cr, 'hr_applicant', 'x_role_status'):
        return

    if not _column_exists(cr, 'hr_job', 'x_role_status'):
        cr.execute("ALTER TABLE hr_job ADD COLUMN x_role_status varchar")
    if not _column_exists(cr, 'hr_job', 'x_sub_status'):
        cr.execute("ALTER TABLE hr_job ADD COLUMN x_sub_status varchar")

    cr.execute("""
        UPDATE hr_job j
        SET x_role_status = agg.x_role_status
        FROM (
            SELECT job_id, x_role_status
            FROM (
                SELECT job_id, x_role_status,
                       ROW_NUMBER() OVER (
                           PARTITION BY job_id ORDER BY COUNT(*) DESC
                       ) AS rn
                FROM hr_applicant
                WHERE job_id IS NOT NULL AND x_role_status IS NOT NULL
                GROUP BY job_id, x_role_status
            ) ranked
            WHERE rn = 1
        ) agg
        WHERE j.id = agg.job_id
          AND (j.x_role_status IS NULL OR j.x_role_status = '')
    """)

    cr.execute("""
        SELECT DISTINCT ON (job_id) job_id, LOWER(TRIM(x_sub_status)) AS sub_text
        FROM hr_applicant
        WHERE job_id IS NOT NULL
          AND x_sub_status IS NOT NULL
          AND TRIM(x_sub_status) != ''
        ORDER BY job_id, id
    """)
    for job_id, sub_text in cr.fetchall():
        key = _SUB_STATUS_MAP.get(sub_text, 'nil')
        cr.execute("""
            UPDATE hr_job
            SET x_sub_status = %s
            WHERE id = %s AND (x_sub_status IS NULL OR x_sub_status = '')
        """, (key, job_id))

    _logger.info('Migrated role/sub status from applicants to job positions.')
