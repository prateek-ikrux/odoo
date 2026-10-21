# -*- coding: utf-8 -*-

# Seed XML id -> billing mode. Consulting needs no entry: it is the default
# every existing type was given when the column arrived.
MODES = {
    'contract_type_fte': 'fte',
    'contract_type_fte_consulting': 'both',
}


def migrate(cr, version):
    """Move billing to where each business is billed.

    Types adopted by pre-migrate keep their own record (noupdate), so their
    billing mode is set here. Every MSA then takes FTE and Consulting from its
    type; one doing both had both kinds of business, so both are ticked.

    Billing used to be agreed on the MSA and copied down onto every SOW. Now
    FTE is billed on the MSA without a billing frequency, and consulting on
    each SOW, by budget rather than bill rate. Each SOW already holds its own
    copy of the old terms, so clearing what no longer applies loses nothing
    that is still shown.

    Plain SQL throughout: an ORM write would mail every contract touched to
    the change notification list.
    """
    if not version:
        return
    for xmlid, mode in MODES.items():
        cr.execute("""
            UPDATE contracts_type t SET billing_mode = %s
              FROM ir_model_data d
             WHERE d.module = 'contracts' AND d.name = %s
               AND d.model = 'contracts.type' AND d.res_id = t.id
        """, [mode, xmlid])

    cr.execute("""
        UPDATE contracts_contract c
           SET is_fte = c.contract_type = 'msa' AND coalesce(t.billing_mode IN ('fte', 'both'), false),
               is_consulting = c.contract_type = 'msa' AND coalesce(t.billing_mode IN ('consulting', 'both'), false)
          FROM contracts_contract c2
          LEFT JOIN contracts_type t ON t.id = c2.type_id
         WHERE c2.id = c.id
    """)

    # An MSA bills FTE only, and never on a cycle; an MSA without FTE bills
    # nothing at all.
    cr.execute("""
        UPDATE contracts_contract
           SET billing_frequency = NULL, budget = NULL
         WHERE contract_type = 'msa'
    """)
    cr.execute("""
        UPDATE contracts_contract
           SET bill_rate = NULL, billing_poc = NULL, billing_start_date = NULL
         WHERE contract_type = 'msa' AND NOT is_fte
    """)
    # A SOW bills consulting, by budget: the bill rate it copied is not one.
    cr.execute("""
        UPDATE contracts_contract SET bill_rate = NULL
         WHERE contract_type = 'sow'
    """)
    # Currency is no longer recorded at all. The columns are left as they are,
    # as Odoo does with any removed field.
