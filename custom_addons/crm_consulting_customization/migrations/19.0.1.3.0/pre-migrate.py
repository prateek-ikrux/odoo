# -*- coding: utf-8 -*-
"""Land Client Type and Industry / Domain on the opportunity for good.

The two used to be the company's, mirrored onto the opportunity by a stored
related field. They are now the opportunity's own, and res.partner no longer
carries them at all.

Because the mirror was stored, every opportunity already holds its own copy in
its own column, and dropping the `related=` leaves that column and its
contents exactly where they are. So this is not a move - it is the sweep for
the rows the mirror never reached: an opportunity created or repointed in the
window before the related field last recomputed, and anything written straight
to the partner column by an import.

Runs pre-migration because the partner columns are read here and are gone by
the time the module has finished loading: a stored field removed from the code
takes its column with it.

What this cannot save is the classification of a company that has no
opportunity - there is no opportunity for it to land on. If those matter, take
a copy of res_partner.client_type and res_partner.industry_domain before
upgrading.
"""
import logging

_logger = logging.getLogger(__name__)

FIELDS = ('client_type', 'industry_domain')


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def migrate(cr, version):
    for field in FIELDS:
        if not _column_exists(cr, 'res_partner', field):
            continue

        # The same hop the related field made: an opportunity opened against a
        # buyer contact takes the classification of the company that contact
        # belongs to. commercial_partner_id points a company back at itself,
        # so the common case reads straight off the client.
        cr.execute("""
            UPDATE crm_lead l
               SET {field} = p.{field}
              FROM res_partner c
              JOIN res_partner p ON p.id = COALESCE(c.commercial_partner_id, c.id)
             WHERE c.id = l.partner_id
               AND l.{field} IS NULL
               AND p.{field} IS NOT NULL
        """.format(field=field))
        if cr.rowcount:
            _logger.info(
                "crm_consulting_customization: %s filled in from the client on "
                "%d opportunit%s", field, cr.rowcount,
                'y' if cr.rowcount == 1 else 'ies')

    # Opportunities left unclassified are left unclassified. Guessing a bucket
    # would put a wrong number in the report and nothing would ever flag it;
    # the field is mandatory on the form, so the next person to open one is
    # asked for the answer.
    cr.execute("""
        SELECT count(*) FROM crm_lead
         WHERE client_type IS NULL OR industry_domain IS NULL
    """)
    remaining = cr.fetchone()[0]
    if remaining:
        _logger.info(
            "crm_consulting_customization: %d opportunit%s still unclassified; "
            "each will be asked for Client Type and Industry / Domain the next "
            "time its form is saved", remaining,
            'y is' if remaining == 1 else 'ies are')
