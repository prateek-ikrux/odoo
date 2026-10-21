# -*- coding: utf-8 -*-
"""Buyers become POCs, and Roles Open becomes a count.

Two renames and one fold, all of which have to happen before the module
finishes loading. A stored field removed from the code takes its column with
it, so anything still sitting in an old column at that point is gone.

  * buyer1_location .. buyer5_location and the rest of the buyer2-5 block are
    renamed to poc*, in place. A rename keeps the data where it is; letting
    the ORM add poc2_name beside an abandoned buyer2_name would not.

  * roles_open_ids, a tag list against crm.role.open, becomes roles_open, a
    number: how many distinct roles the vacancies span. Each opportunity's
    tags are counted into it here, so three tags reads as 3. Nothing in the
    UI can say which three afterwards; only the leftover tables below can.

The crm.role.open model, its seeded roles, its access rules and its
configuration menu go with the field - Odoo removes all of those itself once
nothing in the code declares them. It leaves the crm_role_open and
crm_lead_role_open_rel tables behind, which is the outcome worth having: the
relation table is the only remaining record of which roles an opportunity was
hiring for. Nothing reads either one afterwards.
"""
import logging

_logger = logging.getLogger(__name__)

# old column -> new column. The buyer1 block is the odd one out: three of its
# four fields are crm.lead's own (contact_name, function, phone, email_from)
# and were only ever relabelled, so only the two genuinely new columns appear
# here.
RENAMES = {
    'buyer1_location': 'poc1_location',
}
for n in (2, 3, 4, 5):
    for suffix in ('name', 'designation', 'phone', 'email', 'location'):
        RENAMES['buyer%d_%s' % (n, suffix)] = 'poc%d_%s' % (n, suffix)


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    return cr.fetchone()[0] is not None


def migrate(cr, version):
    renamed = 0
    for old, new in RENAMES.items():
        # Skip anything already renamed - a half-finished upgrade that is run
        # again should not fall over on its own earlier work.
        if not _column_exists(cr, 'crm_lead', old) or _column_exists(cr, 'crm_lead', new):
            continue
        cr.execute('ALTER TABLE crm_lead RENAME COLUMN "%s" TO "%s"' % (old, new))
        renamed += 1
    if renamed:
        _logger.info("crm_consulting_customization: %d buyer columns renamed to "
                     "poc", renamed)

    # Roles Open: from a tag list to a count of it.
    if _table_exists(cr, 'crm_lead_role_open_rel'):
        if not _column_exists(cr, 'crm_lead', 'roles_open'):
            cr.execute('ALTER TABLE crm_lead ADD COLUMN roles_open integer')
        cr.execute("""
            UPDATE crm_lead l
               SET roles_open = counted.total
              FROM (
                    SELECT lead_id, count(DISTINCT role_id) AS total
                      FROM crm_lead_role_open_rel
                     GROUP BY lead_id
                   ) AS counted
             WHERE counted.lead_id = l.id
               AND (l.roles_open IS NULL OR l.roles_open = 0)
        """)
        if cr.rowcount:
            _logger.info("crm_consulting_customization: roles open counted from "
                         "the tag list on %d opportunit%s", cr.rowcount,
                         'y' if cr.rowcount == 1 else 'ies')
