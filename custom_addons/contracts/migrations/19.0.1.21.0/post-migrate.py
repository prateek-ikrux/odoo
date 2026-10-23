# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import SUPERUSER_ID, api

LAKH = 100000


def migrate(cr, version):
    """Budget and Bill Rate trade places, and both become full figures.

    FTE is billed on the MSA by a budget, and consulting on each SOW by a bill
    rate - not the other way round, as they were set up - each entered as the
    full figure rather than in lakhs.

      * An SOW's figure was a budget in lakhs per month. It moves to bill_rate
        as the full figure: 4.5 lakhs becomes 450000.
      * An MSA's was a bill rate in percent, which no budget can be worked out
        from. It is cleared, and a note in the contract's chatter keeps the
        old value, so the Budget can be entered from it.

    Plain SQL for the values: an ORM write would mail every contract touched
    to the change notification list. The note is a chatter note, which mails
    nobody.
    """
    if not version:
        return
    cr.execute("""
        UPDATE contracts_contract
           SET bill_rate = budget * %s, budget = NULL
         WHERE contract_type = 'sow' AND budget IS NOT NULL
    """, [LAKH])
    cr.execute("""
        SELECT id, bill_rate FROM contracts_contract
         WHERE contract_type = 'msa' AND bill_rate IS NOT NULL AND bill_rate != 0
    """)
    old_rates = cr.fetchall()
    if old_rates:
        env = api.Environment(cr, SUPERUSER_ID, {'tracking_disable': True})
        for contract_id, rate in old_rates:
            env['contracts.contract'].browse(contract_id).message_post(
                body=Markup(
                    'FTE is now billed by <b>Budget</b>, entered as the full figure, '
                    'rather than a Bill Rate in percent. This contract\'s Bill Rate '
                    'of <b>%s%%</b> has been cleared: enter its Budget.'
                ) % f'{rate:g}',
                subtype_xmlid='mail.mt_note',
            )
    cr.execute("""
        UPDATE contracts_contract SET bill_rate = NULL
         WHERE contract_type = 'msa'
    """)
