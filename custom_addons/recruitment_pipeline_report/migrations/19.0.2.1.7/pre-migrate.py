# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def _table_exists(cr, table):
    cr.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = %s
    """, (table,))
    return bool(cr.fetchone())


def migrate(cr, version):
    """
    1. Add x_recruiter_id (Many2one) column to hr_applicant.
    2. Seed it from the old x_recruiter_ids m2m table if present.
    3. Drop any leftover relation tables from previous migration attempts.
    """
    # Add Many2one column
    if not _column_exists(cr, 'hr_applicant', 'x_recruiter_id'):
        cr.execute("ALTER TABLE hr_applicant ADD COLUMN x_recruiter_id integer")
        _logger.info('Added x_recruiter_id column to hr_applicant.')

    # Migrate from old m2m table: pick the lowest-id recruiter per applicant
    if _table_exists(cr, 'hr_applicant_recruiter_rel'):
        cr.execute("""
            UPDATE hr_applicant a
            SET x_recruiter_id = rel.user_id
            FROM (
                SELECT applicant_id, MIN(user_id) AS user_id
                FROM hr_applicant_recruiter_rel
                GROUP BY applicant_id
            ) rel
            WHERE a.id = rel.applicant_id
              AND a.x_recruiter_id IS NULL
        """)
        _logger.info('Migrated %s applicant recruiter records (m2m -> m2o).', cr.rowcount)

    # Drop leftover relation tables from earlier migration attempts
    for table in ('hr_applicant_allowed_recruiter_rel',):
        if _table_exists(cr, table):
            cr.execute(f"DROP TABLE {table}")
            _logger.info('Dropped leftover table: %s', table)

    _logger.info('Pre-migration 19.0.2.1.7 complete.')
