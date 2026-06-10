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
    """
    Add new fields required for the Applicant Tracker report.

    hr_applicant columns (new):
        x_candidate_number       – Char
        x_skill                  – Char
        x_total_experience       – Char
        x_relevant_experience    – Char
        x_current_organization   – Char
        x_designation            – Char
        x_education              – Char
        x_current_location       – Char
        x_preferred_location     – Char
        x_notice_period          – Char
        x_current_ctc            – Char
        x_expected_ctc           – Char
        x_offer_in_hand          – Char
        x_reason_for_job_change  – Text
        x_remarks                – Text
        x_client_portal_status   – Char  ('uploaded' | 'not_uploaded')

    hr_job columns (new):
        x_budget                 – Char  (bill rate for Consulting / budget for FTE shown as N/A)
    """

    applicant_char_cols = [
        'x_skill',
        'x_total_experience',
        'x_relevant_experience',
        'x_current_organization',
        'x_designation',
        'x_education',
        'x_current_location',
        'x_preferred_location',
        'x_notice_period',
        'x_current_ctc',
        'x_expected_ctc',
        'x_offer_in_hand',
        'x_client_portal_status',
    ]

    for col in applicant_char_cols:
        if not _column_exists(cr, 'hr_applicant', col):
            cr.execute(f"ALTER TABLE hr_applicant ADD COLUMN {col} varchar")
            _logger.info('Added column hr_applicant.%s', col)

    for col in ('x_reason_for_job_change', 'x_remarks'):
        if not _column_exists(cr, 'hr_applicant', col):
            cr.execute(f"ALTER TABLE hr_applicant ADD COLUMN {col} text")
            _logger.info('Added column hr_applicant.%s', col)

    if not _column_exists(cr, 'hr_job', 'x_budget'):
        cr.execute("ALTER TABLE hr_job ADD COLUMN x_budget varchar")
        _logger.info('Added column hr_job.x_budget')

    _logger.info('Pre-migration 19.0.2.1.8 complete.')
