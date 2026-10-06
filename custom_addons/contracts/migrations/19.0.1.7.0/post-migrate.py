# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Bring the billing terms of placed contracts in line with their parent.

    The billing fields became computed from the parent contract after some
    placed contracts may already have been given terms of their own; an
    existing column is not recomputed on its own, so it is done here.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {'contracts_billing_sync': True})
    placed = env['contracts.contract'].with_context(active_test=False).search([
        ('contract_type', '=', 'sow'),
    ])
    placed._compute_billing()
    placed.flush_recordset()
