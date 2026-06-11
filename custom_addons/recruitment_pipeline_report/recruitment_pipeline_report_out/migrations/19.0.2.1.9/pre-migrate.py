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
    """Add assessment fields to hr_applicant."""
    for col, coltype in [
        ('x_assessment_link_received', "VARCHAR"),
        ('x_assessment_taken',         "VARCHAR"),
        ('x_assessment_feedback',      "VARCHAR"),
    ]:
        if not _column_exists(cr, 'hr_applicant', col):
            cr.execute(f"ALTER TABLE hr_applicant ADD COLUMN {col} {coltype}")
            _logger.info('Added hr_applicant.%s', col)

    _logger.info('Pre-migration 19.0.2.1.9 complete.')
