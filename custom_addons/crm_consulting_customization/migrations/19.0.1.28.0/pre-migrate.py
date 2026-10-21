# -*- coding: utf-8 -*-
from odoo.addons.crm_consulting_customization.models.crm_lead import fill_last_activity_dates


def migrate(cr, version):
    """Give every opportunity its last activity before the registry loads.

    Created here, in SQL, so the upgrade finds the column already there and
    filled from each opportunity's own history, rather than adding it with
    the field's default and dating every opportunity today.
    """
    if not version:
        return
    cr.execute("""
        ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS last_activity_date timestamp
    """)
    fill_last_activity_dates(cr)
