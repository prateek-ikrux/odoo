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
    """Backfill hr_applicant.department_id (Client) from the linked
    hr_job.department_id wherever they differ.

    Historically department_id was only synced onto an applicant at the
    moment job_id was set (see hr_applicant.py create/write). Two gaps
    left some applicants with a blank or stale Client even though they
    are clearly linked to a job:
      1. The job itself had no Client set at the time (department_id
         wasn't required on hr.job until a later version of this module).
      2. The job's Client was added/changed after applicants were
         already linked to it, with nothing to cascade the update down.

    This is a one-time backfill; the write() override added to
    hr_job.py keeps future Client changes in sync going forward.
    """
    if not (_column_exists(cr, 'hr_applicant', 'department_id')
            and _column_exists(cr, 'hr_applicant', 'job_id')
            and _column_exists(cr, 'hr_job', 'department_id')):
        return

    cr.execute("""
        UPDATE hr_applicant a
        SET department_id = j.department_id
        FROM hr_job j
        WHERE a.job_id = j.id
          AND j.department_id IS NOT NULL
          AND (a.department_id IS NULL OR a.department_id != j.department_id)
    """)
    updated = cr.rowcount
    _logger.info(
        'Backfilled Client (department_id) on %s applicant record(s) from their linked job.',
        updated,
    )
