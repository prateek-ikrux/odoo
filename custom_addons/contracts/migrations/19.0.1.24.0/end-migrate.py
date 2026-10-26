# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Drop what the Contract Types master list leaves behind.

    Odoo drops a removed model's table only when the module is uninstalled,
    so on an upgrade the master list's table, and the export filter's link
    table to it, would stay on with nothing reading them. Every MSA's type
    was copied onto the MSA by pre-migrate before the module loaded.
    """
    if not version:
        return
    cr.execute("DROP TABLE IF EXISTS contracts_report_wizard_contracts_type_rel")
    cr.execute("DROP TABLE IF EXISTS contracts_type CASCADE")
