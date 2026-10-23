# -*- coding: utf-8 -*-


def migrate(cr, version):
    """A placed contract's Contract POC is now its parent's, as its client
    already was, so every SOW takes the POC of the MSA it sits under.

    Billing POC is gone: Odoo drops its column with the field, and the audit
    log keeps any past change to it.

    Plain SQL: an ORM write would mail every contract touched to the change
    notification list.
    """
    if not version:
        return
    cr.execute("""
        UPDATE contracts_contract sow
           SET poc = parent.poc
          FROM contracts_contract parent
         WHERE sow.contract_type = 'sow'
           AND sow.parent_contract_id = parent.id
           AND sow.poc IS DISTINCT FROM parent.poc
    """)
