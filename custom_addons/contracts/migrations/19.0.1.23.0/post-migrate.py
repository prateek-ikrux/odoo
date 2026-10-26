# -*- coding: utf-8 -*-


def migrate(cr, version):
    """FTE billing gets a date and a guarantee of its own, and an FTE MSA is
    no longer extended.

      * FTE is billed on a Billing Date of its own; the Billing Start Date is
        a consulting one, on the SOW. An MSA's date moves across.
      * An MSA doing FTE alone is never extended, so any extension recorded
        on one is taken back, and it runs to its end date again.

    Gross Profit Margin, a stored compute, is worked out for every SOW by Odoo
    when its column is added. FTE placements are a new table.

    Plain SQL: an ORM write would mail every contract touched to the change
    notification list.
    """
    if not version:
        return
    cr.execute("""
        UPDATE contracts_contract
           SET billing_date = billing_start_date, billing_start_date = NULL
         WHERE contract_type = 'msa' AND billing_start_date IS NOT NULL
    """)
    # The contract's own Contract Type since 19.0.1.24.0, whose pre-migrate
    # fills it before this runs on a database upgrading past both at once.
    cr.execute("""
        UPDATE contracts_contract c
           SET is_extended = 'no', extended_end_date = NULL,
               effective_end_date = c.end_date,
               reminder_sent_days = 0, reminder_last_sent = NULL
         WHERE c.billing_mode = 'fte'
           AND c.contract_type = 'msa'
           AND (c.is_extended = 'yes' OR c.extended_end_date IS NOT NULL)
    """)
