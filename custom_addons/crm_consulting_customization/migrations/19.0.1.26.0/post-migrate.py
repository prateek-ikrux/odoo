# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from odoo.addons.crm_consulting_customization.models.crm_lead import PRIMARY_POC_FIELDS


def migrate(cr, version):
    """Every POC goes in the one list, the first of them the primary.

    POC 1 lived in the opportunity's own contact fields, shown on the form
    apart from the list of the others. It becomes the first row of the list,
    ahead of every POC already there - only where it holds anything, as a
    POC 1 with only a phone number is still a POC worth keeping.

    The contact fields stay, as a copy of whichever POC is first. They already
    match the row made from them; an opportunity whose POC 1 was empty but
    which had further POCs takes its copy from the first of those.
    """
    if not version:
        return
    lead_columns = list(PRIMARY_POC_FIELDS)
    poc_columns = [PRIMARY_POC_FIELDS[f] for f in lead_columns]
    cr.execute("""
        INSERT INTO crm_lead_poc (lead_id, sequence, {poc_columns},
                                  create_uid, create_date, write_uid, write_date)
        SELECT l.id,
               COALESCE((SELECT MIN(p.sequence) FROM crm_lead_poc p WHERE p.lead_id = l.id), 11) - 1,
               {lead_columns},
               COALESCE(l.write_uid, l.create_uid), now() AT TIME ZONE 'UTC',
               COALESCE(l.write_uid, l.create_uid), now() AT TIME ZONE 'UTC'
          FROM crm_lead l
         WHERE {any_filled}
         ORDER BY l.id
    """.format(
        poc_columns=', '.join(poc_columns),
        lead_columns=', '.join('l.%s' % f for f in lead_columns),
        any_filled=' OR '.join("COALESCE(TRIM(l.%s), '') <> ''" % f for f in lead_columns),
    ))
    env = api.Environment(cr, SUPERUSER_ID, {})
    Lead = env['crm.lead'].with_context(active_test=False)
    leads = Lead.search([('poc_ids', '!=', False)])
    for fname in PRIMARY_POC_FIELDS:
        env.add_to_compute(Lead._fields[fname], leads)
    leads.flush_recordset()
