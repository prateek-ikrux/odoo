# -*- coding: utf-8 -*-
"""Client Type and Industry / Domain stop being selections.

Both become many2ones to a master list, under the same names. The ORM cannot
turn a column of codes into a column of ids, so before the module loads each
old column is moved aside to <field>_legacy, where post-migrate.py finds it,
and the ORM creates the new column fresh. Only a text column is moved, so this
is safe to re-run.
"""
import logging

_logger = logging.getLogger(__name__)

FIELDS = ('client_type', 'industry_domain')


def _column_type(cr, table, column):
    cr.execute("""
        SELECT data_type FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (table, column))
    row = cr.fetchone()
    return row and row[0]


def migrate(cr, version):
    for field in FIELDS:
        if _column_type(cr, 'crm_lead', field) != 'character varying':
            continue
        if _column_type(cr, 'crm_lead', field + '_legacy'):
            continue
        cr.execute('ALTER TABLE crm_lead RENAME COLUMN "%s" TO "%s_legacy"' % (field, field))
        _logger.info("crm_consulting_customization: crm_lead.%s moved aside to %s_legacy", field, field)
