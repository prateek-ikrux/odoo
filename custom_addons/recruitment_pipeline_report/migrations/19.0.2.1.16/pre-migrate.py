# -*- coding: utf-8 -*-
"""Migration 19.0.2.1.16

Clear x_lwd for any existing applicants whose notice period does not
warrant a Last Working Date (i.e. not serving_notice or immediate_joiner).
"""
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE hr_applicant
           SET x_lwd = NULL
         WHERE x_lwd IS NOT NULL
           AND (x_notice_period IS NULL
                OR x_notice_period NOT IN ('serving_notice', 'immediate_joiner'))
    """)
    _logger.info(
        'Cleared x_lwd on %d applicant(s) with non-applicable notice period.',
        cr.rowcount,
    )
