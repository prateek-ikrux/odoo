# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """FTE is billed per hire: the Billing Date moves from the MSA to each FTE
    placement, and the MSA keeps the FTE terms - budget, guarantee period and
    a standard fee - instead.

    An MSA's own billing date belongs to no single hire, so it cannot be moved
    onto one. A note in the MSA's chatter keeps it before Odoo drops the
    column, which happens once the module has loaded, after this runs. The
    note mails nobody.

    An FTE MSA can be extended again; nothing to change for that.
    """
    if not version:
        return
    cr.execute("""
        SELECT id, billing_date FROM contracts_contract
         WHERE contract_type = 'msa' AND billing_date IS NOT NULL
    """)
    rows = cr.fetchall()
    if not rows:
        return
    env = api.Environment(cr, SUPERUSER_ID, {'tracking_disable': True})
    for contract_id, billing_date in rows:
        env['contracts.contract'].browse(contract_id).message_post(
            body=Markup(
                'FTE is now billed on each FTE placement, each with its own '
                '<b>Billing Date</b>. This contract\'s Billing Date of <b>%s</b> '
                'has been removed: set it on the placements it applied to.'
            ) % billing_date.strftime('%d/%m/%Y'),
            subtype_xmlid='mail.mt_note',
        )
