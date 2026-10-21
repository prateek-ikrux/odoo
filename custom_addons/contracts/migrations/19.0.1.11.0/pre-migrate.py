# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Adopt a hand-made Consulting type as the seeded one.

    Contract types could be created before the Consulting seed record shipped.
    Loading the seed over one already named Consulting would break on the
    unique name, so the existing record is given the seed's XML id instead,
    flagged noupdate so the data file leaves it as it is.
    """
    if not version:
        return
    cr.execute("SELECT to_regclass('contracts_type')")
    if not cr.fetchone()[0]:
        return
    cr.execute("""
        SELECT 1 FROM ir_model_data
         WHERE module = 'contracts' AND name = 'contract_type_consulting'
    """)
    if cr.fetchone():
        return
    cr.execute("""
        SELECT id FROM contracts_type
         WHERE lower(trim(name)) = 'consulting'
         ORDER BY id LIMIT 1
    """)
    row = cr.fetchone()
    if row:
        cr.execute("""
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            VALUES ('contracts', 'contract_type_consulting', 'contracts.type', %s, true)
        """, [row[0]])
