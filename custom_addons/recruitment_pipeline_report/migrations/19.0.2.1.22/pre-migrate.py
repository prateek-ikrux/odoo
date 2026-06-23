# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def _extract_numeric_text(cr, table, column):
    """Overwrite a text column in-place with just the first numeric token
    found in each value (supports decimals, e.g. '5.5 Yrs' -> '5.5',
    '5+ years' -> '5', '7 yrs exp' -> '7'). Values with no numeric token
    are cleared to NULL. Must run before the ORM changes the column's
    Postgres type from text to float, since a direct cast would error
    or silently null out anything non-numeric (e.g. 'Yrs')."""
    cr.execute(f"""
        UPDATE {table}
        SET {column} = (regexp_match({column}, '(\\d+(\\.\\d+)?)'))[1]
        WHERE {column} IS NOT NULL
          AND {column} ~ '\\d'
    """)
    affected = cr.rowcount
    cr.execute(f"""
        UPDATE {table}
        SET {column} = NULL
        WHERE {column} IS NOT NULL
          AND {column} !~ '^\\d+(\\.\\d+)?$'
    """)
    cleared = cr.rowcount
    _logger.info(
        'Extracted numeric value in %s.%s for %s row(s); cleared %s '
        'non-numeric remaining value(s) to NULL.',
        table, column, affected, cleared,
    )


def migrate(cr, version):
    """Convert x_total_experience / x_relevant_experience from free text
    (e.g. '5.5 Yrs') to a plain numeric string in-place, so the upcoming
    ORM column-type change (Char -> Float) on these fields doesn't fail
    or wipe out existing applicant data."""
    table = 'hr_applicant'
    for column in ('x_total_experience', 'x_relevant_experience'):
        if _column_exists(cr, table, column):
            _extract_numeric_text(cr, table, column)
