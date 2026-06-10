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
    """Rename x_rec_id → x_req_id on hr_job and hr_applicant."""
    if _column_exists(cr, 'hr_job', 'x_rec_id') and \
       not _column_exists(cr, 'hr_job', 'x_req_id'):
        cr.execute('ALTER TABLE hr_job RENAME COLUMN x_rec_id TO x_req_id')
        _logger.info('Renamed hr_job.x_rec_id -> x_req_id')

    if _column_exists(cr, 'hr_applicant', 'x_rec_id') and \
       not _column_exists(cr, 'hr_applicant', 'x_req_id'):
        cr.execute('ALTER TABLE hr_applicant RENAME COLUMN x_rec_id TO x_req_id')
        _logger.info('Renamed hr_applicant.x_rec_id -> x_req_id')
