# -*- coding: utf-8 -*-
"""Finish the 19.0.1.19.0 upgrade on databases where it stopped at the end.

On some Odoo 19 builds the 19.0.1.19.0 upgrade commits its migration and its
version, then fails while unlinking the old Client Type and Industry / Domain
selection options ("AttributeError: 'str' object has no attribute 'get'").
Every retry after that skips the 19.0.1.19.0 scripts, because the database
already records that version, and fails the same way. This removes those
options before the module loads, so nothing is left for the end of the
upgrade to trip over. A database the 19.0.1.19.0 pre-migrate already cleaned
has nothing to remove, so this is safe everywhere and safe to re-run.
"""
import logging

_logger = logging.getLogger(__name__)

FIELDS = ('client_type', 'industry_domain')


def migrate(cr, version):
    cr.execute("""
        SELECT s.id FROM ir_model_fields_selection s
          JOIN ir_model_fields f ON f.id = s.field_id
         WHERE f.model = 'crm.lead' AND f.name IN %s
    """, (FIELDS,))
    ids = tuple(row[0] for row in cr.fetchall())
    if not ids:
        return
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE model = 'ir.model.fields.selection' AND res_id IN %s
    """, (ids,))
    cr.execute("DELETE FROM ir_model_fields_selection WHERE id IN %s", (ids,))
    _logger.info("crm_consulting_customization: %s leftover selection options of %s removed",
                 len(ids), ', '.join(FIELDS))
