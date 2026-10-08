# -*- coding: utf-8 -*-
"""Client Status drops Dormant and Passive for a single Inactive.

Runs before the module loads, while the old values are still in the column.
Left to the ORM, the removed options would leave those opportunities holding
a value the field no longer offers. Both fold into Inactive; Active stays as
it is. Safe to re-run.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE crm_lead
           SET client_status = 'inactive'
         WHERE client_status IN ('dormant', 'passive')
    """)
    _logger.info(
        "crm_consulting_customization: %s opportunities moved to Inactive client status",
        cr.rowcount,
    )
