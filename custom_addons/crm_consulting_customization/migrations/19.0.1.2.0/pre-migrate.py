# -*- coding: utf-8 -*-
"""Fold the separate Buyer Contact 1 fields back onto the opportunity's own.

Buyer Contact 1 was first built as four new columns - buyer1_name,
buyer1_designation, buyer1_phone, buyer1_email - beside the contact name, job
position, phone and email an opportunity already carried. They were the same
four things twice: the person being dealt with is the primary buyer. The new
columns are gone and Buyer Contact 1 is the original fields, relabelled.

Anything typed into the old columns is moved across here, before the fields
disappear, and only where the destination is empty - a value somebody entered
in the field that was actually wired to Send Email is not overwritten by one
entered in its duplicate.

Runs pre-migration so it reads the old columns while they still exist.
"""
import logging

_logger = logging.getLogger(__name__)

# old column -> the field it is folded into
FOLD = {
    'buyer1_name': 'contact_name',
    'buyer1_designation': 'function',
    'buyer1_phone': 'phone',
    'buyer1_email': 'email_from',
}


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def migrate(cr, version):
    for old, new in FOLD.items():
        if not _column_exists(cr, 'crm_lead', old):
            continue
        cr.execute("""
            UPDATE crm_lead
               SET {new} = {old}
             WHERE {old} IS NOT NULL
               AND {old} <> ''
               AND ({new} IS NULL OR {new} = '')
        """.format(old=old, new=new))
        if cr.rowcount:
            _logger.info("crm_consulting_customization: folded %s into %s on %d "
                         "opportunit%s", old, new, cr.rowcount,
                         'y' if cr.rowcount == 1 else 'ies')

        # The column itself is left in place. Odoo never drops a column on its
        # own, and dropping it here would throw away the only copy of anything
        # this fold declined to overwrite. It is inert once the field is gone,
        # and safe to drop by hand after the fold has been checked.
