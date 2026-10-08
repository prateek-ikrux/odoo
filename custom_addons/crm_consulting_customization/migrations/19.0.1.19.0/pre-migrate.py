# -*- coding: utf-8 -*-
"""Client Type and Industry / Domain stop being selections.

Both become many2ones to a master list, under the same names. The ORM cannot
turn a column of codes into a column of ids, so before the module loads each
old column is moved aside to <field>_legacy, where post-migrate.py finds it,
and the ORM creates the new column fresh. Only a text column is moved, so this
is safe to re-run.

The old selection options are deleted here too, with their external ids.
Left in place, the end of the upgrade unlinks them itself, and some Odoo 19
builds then read the field's ondelete as a selection's dict when it is now a
many2one's string, failing the whole upgrade with
"AttributeError: 'str' object has no attribute 'get'". Later builds skip a
field that changed type; doing it here works on both.
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


def _drop_selection_options(cr, model, fields):
    cr.execute("""
        SELECT s.id FROM ir_model_fields_selection s
          JOIN ir_model_fields f ON f.id = s.field_id
         WHERE f.model = %s AND f.name IN %s
    """, (model, tuple(fields)))
    ids = tuple(row[0] for row in cr.fetchall())
    if not ids:
        return
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE model = 'ir.model.fields.selection' AND res_id IN %s
    """, (ids,))
    cr.execute("DELETE FROM ir_model_fields_selection WHERE id IN %s", (ids,))
    _logger.info("crm_consulting_customization: %s old selection options of %s removed",
                 len(ids), ', '.join(fields))


def migrate(cr, version):
    _drop_selection_options(cr, 'crm.lead', FIELDS)
    for field in FIELDS:
        if _column_type(cr, 'crm_lead', field) != 'character varying':
            continue
        if _column_type(cr, 'crm_lead', field + '_legacy'):
            continue
        cr.execute('ALTER TABLE crm_lead RENAME COLUMN "%s" TO "%s_legacy"' % (field, field))
        _logger.info("crm_consulting_customization: crm_lead.%s moved aside to %s_legacy", field, field)
