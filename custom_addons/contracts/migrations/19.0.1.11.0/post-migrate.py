# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Let Consulting take SOWs, and type the MSAs that already have them.

    SOWs are only ever placed under consulting contracts, so any untyped MSA
    with one is a consulting MSA. Without this, the rule that an SOW's parent
    must be of a type allowing SOWs would leave those MSAs unpickable for new
    placements until someone typed each of them by hand.

    The Consulting type may have been adopted from one made by hand (see
    pre-migrate), in which case the seed's noupdate record did not set the
    flag on it, so it is set here.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    consulting = env.ref('contracts.contract_type_consulting', raise_if_not_found=False)
    if not consulting:
        return
    if not consulting.allows_sow:
        consulting.allows_sow = True
    msas = env['contracts.contract'].with_context(active_test=False).search([
        ('contract_type', '=', 'msa'),
        ('type_id', '=', False),
        ('child_contract_ids', '!=', False),
    ])
    msas.write({'type_id': consulting.id})
