# -*- coding: utf-8 -*-
"""Put every opportunity back on its Client Type and Industry / Domain.

By now the module has loaded and seeded both master lists, one entry per old
selection code, each under the external id <field>_<code>. Each opportunity
is pointed at the entry for the code in its <field>_legacy column, and the
legacy column is dropped once nothing is left in it.

A code with no seeded entry - one added by hand to the old selection - gets an
entry of its own, named after the code, so no opportunity loses its
classification. Rename it under CRM > Configuration afterwards.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

FIELDS = {
    'client_type': 'crm.client.type',
    'industry_domain': 'crm.industry.domain',
}


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for field, model in FIELDS.items():
        legacy = field + '_legacy'
        if not _column_exists(cr, 'crm_lead', legacy):
            continue
        cr.execute('SELECT DISTINCT "%s" FROM crm_lead WHERE "%s" IS NOT NULL' % (legacy, legacy))
        for (code,) in cr.fetchall():
            entry = env.ref('crm_consulting_customization.%s_%s' % (field, code), raise_if_not_found=False)
            if not entry:
                Model = env[model].with_context(active_test=False)
                entry = Model.search([('name', '=', code)], limit=1) or Model.create({'name': code})
                _logger.warning("crm_consulting_customization: %s code %r had no seeded entry; "
                                "created %r", field, code, entry.name)
            cr.execute('UPDATE crm_lead SET "%s" = %%s WHERE "%s" = %%s' % (field, legacy),
                       (entry.id, code))
            _logger.info("crm_consulting_customization: %s opportunities moved to %s %r",
                         cr.rowcount, field, entry.name)
        cr.execute('ALTER TABLE crm_lead DROP COLUMN "%s"' % legacy)
    env['crm.lead'].invalidate_model(list(FIELDS))
