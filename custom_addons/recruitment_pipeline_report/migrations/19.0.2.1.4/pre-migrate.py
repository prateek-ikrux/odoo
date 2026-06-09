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
    """Backup res.users POC ids before changing x_poc_id to res.partner."""
    if not _column_exists(cr, 'hr_job', 'x_poc_id'):
        return

    if not _column_exists(cr, 'hr_job', 'x_poc_user_id_backup'):
        cr.execute("ALTER TABLE hr_job ADD COLUMN x_poc_user_id_backup integer")

    cr.execute("""
        UPDATE hr_job
        SET x_poc_user_id_backup = x_poc_id
        WHERE x_poc_id IS NOT NULL
          AND (x_poc_user_id_backup IS NULL OR x_poc_user_id_backup != x_poc_id)
    """)
    cr.execute("UPDATE hr_job SET x_poc_id = NULL")

    if _column_exists(cr, 'hr_applicant', 'x_poc_id'):
        cr.execute("UPDATE hr_applicant SET x_poc_id = NULL")

    _logger.info('Backed up job POC user ids before partner migration.')
