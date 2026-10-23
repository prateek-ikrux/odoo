# -*- coding: utf-8 -*-
"""POC changes join the audit log, through crm_lead.poc_summary.

The column is added and filled here, before the module loads, rather than
left to the ORM. A new stored computed field is computed for every record as
it is added, and a tracked one logs that as a change: every opportunity with
a POC would get an audit log entry and a change notification on upgrade.
Filled in advance, the column is already up to date and nothing is logged.
"""
import logging

from odoo.addons.crm_consulting_customization.models.crm_lead import (
    POC_SUMMARY_FIELDS, poc_summary_line,
)

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS poc_summary text")
    cr.execute(f"""
        SELECT lead_id, {', '.join(POC_SUMMARY_FIELDS)}
          FROM crm_lead_poc
         ORDER BY lead_id, sequence, id
    """)
    lines = {}
    for row in cr.dictfetchall():
        if line := poc_summary_line(row):
            lines.setdefault(row['lead_id'], []).append(line)
    for lead_id, lead_lines in lines.items():
        cr.execute("UPDATE crm_lead SET poc_summary = %s WHERE id = %s",
                   ['\n'.join(lead_lines), lead_id])
    _logger.info("POC List filled for %s opportunities.", len(lines))
