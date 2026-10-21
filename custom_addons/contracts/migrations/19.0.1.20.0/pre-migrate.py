# -*- coding: utf-8 -*-

# Seed XML id -> the name a hand-made type of that kind goes by.
SEEDS = {
    'contract_type_fte': 'fte',
    'contract_type_fte_consulting': 'fte/consulting',
}


def migrate(cr, version):
    """Adopt hand-made FTE and FTE/Consulting types as the seeded ones.

    Both were created by hand before they were seeded. Loading the seed over
    one already carrying the name would break on the unique name, so the
    existing record is given the seed's XML id instead, flagged noupdate so
    the data file leaves it as it is. Its billing mode is set in post-migrate.
    """
    if not version:
        return
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
