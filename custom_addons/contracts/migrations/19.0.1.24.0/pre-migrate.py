# -*- coding: utf-8 -*-


def migrate(cr, version):
    """The Contract Types master list gives way to a fixed choice of three on
    the contract itself: Consulting, FTE and FTE/Consulting.

    Each MSA's Contract Type is filled here from the billing mode of the type
    it had, while that type can still be read: once the module has loaded,
    Odoo drops the contracts_type table and the contract's type_id column,
    as it does with any model or field no longer in the code. The audit log
    keeps any past change of type.
    """
    if not version:
        return
    cr.execute("ALTER TABLE contracts_contract ADD COLUMN IF NOT EXISTS billing_mode varchar")
    cr.execute("SELECT to_regclass('contracts_type')")
    if cr.fetchone()[0]:
        cr.execute("""
            UPDATE contracts_contract c
               SET billing_mode = t.billing_mode
              FROM contracts_type t
             WHERE c.type_id = t.id AND c.contract_type = 'msa'
        """)
    # An MSA left without one - none should be - takes the default.
    cr.execute("""
        UPDATE contracts_contract SET billing_mode = 'consulting'
         WHERE contract_type = 'msa' AND billing_mode IS NULL
    """)
