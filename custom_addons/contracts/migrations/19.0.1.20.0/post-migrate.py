# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Clear billing that no longer applies where it now sits.

    The billing mode is filled by pre-migrate. Billing used to be agreed on
    the MSA and copied down onto every SOW. Now FTE is billed on the MSA
    without a billing frequency, and consulting on each SOW, by budget rather
    than bill rate. Each SOW already holds its own copy of the old terms, so
    clearing what no longer applies loses nothing that is still shown.

    Plain SQL throughout: an ORM write would mail every contract touched to
    the change notification list.
    """
    if not version:
        return
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
         WHERE contract_type = 'msa'
           AND (type_id IS NULL
                OR type_id NOT IN (SELECT id FROM contracts_type
                                    WHERE billing_mode IN ('fte', 'both')))
    """)
    # A SOW bills consulting, by budget: the bill rate it copied is not one.
    cr.execute("""
        UPDATE contracts_contract SET bill_rate = NULL
         WHERE contract_type = 'sow'
    """)
    # Currency is no longer recorded at all. The columns are left as they are,
    # as Odoo does with any removed field.
