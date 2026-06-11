# -*- coding: utf-8 -*-
"""
Migration 19.0.2.1.10 – pre-migrate
Convert x_notice_period on hr.applicant from free-text Char to Selection.

Mapping (case-insensitive, stripped):
  "30"  / "30 days"  / "30days"       → 30_days
  "60"  / "60 days"  / "60days"       → 60_days
  "90"  / "90 days"  / "90days"       → 90_days
  "immediate" / "immediate joiner"     → immediate_joiner
  anything else                        → NULL  (unknown values cleared)
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        UPDATE hr_applicant
        SET x_notice_period =
            CASE
                WHEN LOWER(TRIM(x_notice_period)) IN ('30', '30 days', '30days')
                    THEN '30_days'
                WHEN LOWER(TRIM(x_notice_period)) IN ('60', '60 days', '60days')
                    THEN '60_days'
                WHEN LOWER(TRIM(x_notice_period)) IN ('90', '90 days', '90days')
                    THEN '90_days'
                WHEN LOWER(TRIM(x_notice_period)) LIKE 'immediate%'
                    THEN 'immediate_joiner'
                ELSE NULL
            END
        WHERE x_notice_period IS NOT NULL
          AND TRIM(x_notice_period) != ''
    """)
