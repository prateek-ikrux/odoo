# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

_VALID_SUB_STATUS = ('candidate_drop', 'drop_by_client', 'on_hold_alignment', 'nil')
_VALID_ROLE_STATUS = ('active', 'in_progress', 'on_hold', 'closed')

# Legacy free-text values → selection keys
_SUB_STATUS_LEGACY = {
    'on hold': 'on_hold_alignment',
    'on hold due to alignment': 'on_hold_alignment',
    'candidate drop': 'candidate_drop',
    'drop by client': 'drop_by_client',
    'nil': 'nil',
    'nil/not applicable': 'nil',
    'n/a': 'nil',
    'not applicable': 'nil',
}


def _sanitize_sub_status(value):
    if not value:
        return None
    if value in _VALID_SUB_STATUS:
        return value
    return _SUB_STATUS_LEGACY.get(str(value).strip().lower())


def migrate(cr, version):
    """Resync stored related fields and remove legacy free-text selection values."""
    cr.execute("""
        UPDATE hr_job
        SET x_sub_status = NULL
        WHERE x_sub_status IS NOT NULL
          AND x_sub_status NOT IN %s
    """, (_VALID_SUB_STATUS,))

    cr.execute("SELECT id, x_sub_status FROM hr_job WHERE x_sub_status IS NOT NULL")
    for job_id, sub_status in cr.fetchall():
        mapped = _sanitize_sub_status(sub_status)
        if mapped != sub_status:
            cr.execute("UPDATE hr_job SET x_sub_status = %s WHERE id = %s", (mapped, job_id))

    cr.execute("""
        UPDATE hr_applicant a
        SET x_sub_status = j.x_sub_status,
            x_role_status = COALESCE(j.x_role_status, 'active')
        FROM hr_job j
        WHERE a.job_id = j.id
    """)

    cr.execute("""
        UPDATE hr_applicant
        SET x_sub_status = NULL
        WHERE x_sub_status IS NOT NULL
          AND x_sub_status NOT IN %s
    """, (_VALID_SUB_STATUS,))

    cr.execute("""
        UPDATE hr_applicant
        SET x_role_status = 'active'
        WHERE x_role_status IS NOT NULL
          AND x_role_status NOT IN %s
    """, (_VALID_ROLE_STATUS,))

    cr.execute("""
        UPDATE hr_applicant
        SET x_sub_status = NULL, x_role_status = 'active'
        WHERE job_id IS NULL
          AND (x_sub_status IS NOT NULL OR x_role_status NOT IN %s)
    """, (_VALID_ROLE_STATUS,))

    _logger.info('Sanitized role/sub status selection values on jobs and applicants.')
