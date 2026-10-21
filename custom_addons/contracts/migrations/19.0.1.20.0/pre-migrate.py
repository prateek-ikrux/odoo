# -*- coding: utf-8 -*-

# Seed XML id -> the name a hand-made type of that kind goes by.
SEEDS = {
    'contract_type_fte': 'fte',
    'contract_type_fte_consulting': 'fte/consulting',
}

# Seed XML id -> billing mode. Every other type is Consulting.
MODES = {
    'contract_type_fte': 'fte',
    'contract_type_fte_consulting': 'both',
}


def migrate(cr, version):
    """Adopt the hand-made types and give each its billing mode up front.

    FTE and FTE/Consulting were created by hand before they were seeded.
    Loading the seed over one already carrying the name would break on the
    unique name, so the existing record is given the seed's XML id instead,
    flagged noupdate so the data file leaves it as it is.

    The billing mode is then created and filled here, in SQL, before the
    registry loads, so no contract is ever seen with its type sitting on the
    column's default of Consulting - not by a stored compute, and not by the
    change notifications that report on one.
    """
    if not version:
        return
    _adopt_seeds(cr)
    _fill_billing_mode(cr)


def _adopt_seeds(cr):
    for xmlid, name in SEEDS.items():
        cr.execute("""
            SELECT 1 FROM ir_model_data
             WHERE module = 'contracts' AND name = %s
        """, [xmlid])
        if cr.fetchone():
            continue
        cr.execute("""
            SELECT id FROM contracts_type
             WHERE lower(regexp_replace(name, '[[:space:]]', '', 'g')) = %s
             ORDER BY id LIMIT 1
        """, [name])
        row = cr.fetchone()
        if row:
            cr.execute("""
                INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
                VALUES ('contracts', %s, 'contracts.type', %s, true)
            """, [xmlid, row[0]])


def _fill_billing_mode(cr):
    cr.execute("""
        ALTER TABLE contracts_type
            ADD COLUMN IF NOT EXISTS billing_mode varchar
    """)
    cr.execute("""
        UPDATE contracts_type SET billing_mode = 'consulting'
         WHERE billing_mode IS NULL
    """)
    for xmlid, mode in MODES.items():
        cr.execute("""
            UPDATE contracts_type t SET billing_mode = %s
              FROM ir_model_data d
             WHERE d.module = 'contracts' AND d.name = %s
               AND d.model = 'contracts.type' AND d.res_id = t.id
        """, [mode, xmlid])
