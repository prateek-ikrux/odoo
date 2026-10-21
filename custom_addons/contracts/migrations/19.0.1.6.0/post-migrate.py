# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Answer the two new Yes/No questions for contracts that predate them.

    The new columns start out on their default of No. Left that way, the next
    write would wipe extended dates already on record, and every placed
    contract would lose the appraisal date it has always carried.
    """
    if not version:
        return
    cr.execute("""
        UPDATE contracts_contract
           SET is_extended = 'yes'
         WHERE extended_end_date IS NOT NULL
    """)
    cr.execute("""
        UPDATE contracts_contract
           SET is_appraisal_due = 'yes'
         WHERE contract_type = 'sow'
    """)
    # The appraisal date now depends on the answer, so bring the stored value
    # in line: kept on the placed contracts, cleared on the overarching ones.
    env = api.Environment(cr, SUPERUSER_ID, {})
    contracts = env['contracts.contract'].with_context(active_test=False).search([])
    contracts.invalidate_recordset(['is_extended', 'is_appraisal_due'])
    contracts._compute_annual_appraisal_due()
    contracts.flush_recordset(['annual_appraisal_due'])
