# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Remove the workbooks earlier exports left behind.

    Every Excel export used to be saved as an attachment that nothing pointed
    at and nothing ever deleted. The export now hands the file over from the
    transient wizard instead, so the ones already stored are only clutter.

    Matched narrowly: the two fixed export file names, attached to no record,
    and not linked to a contract as one of its documents.
    """
    if not version:
        return
    cr.execute("""
        SELECT a.id
          FROM ir_attachment a
         WHERE a.name IN ('MSA_Report.xlsx', 'SOW_Report.xlsx')
           AND a.res_model IS NULL
           AND COALESCE(a.res_id, 0) = 0
           AND NOT EXISTS (
                SELECT 1 FROM contracts_contract_attachment_rel r
                 WHERE r.attachment_id = a.id
           )
    """)
    ids = [row[0] for row in cr.fetchall()]
    if ids:
        env = api.Environment(cr, SUPERUSER_ID, {})
        env['ir.attachment'].browse(ids).unlink()
