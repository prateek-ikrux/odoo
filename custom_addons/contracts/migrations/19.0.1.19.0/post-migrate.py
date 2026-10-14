# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Change notifications go back to one email per change, sent as it
    happens. The end-of-day summary job is noupdate data, so the upgrade
    would otherwise leave it behind, pointing at a queue that no longer
    exists; the queue table itself goes with its model."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    cron = env.ref('contracts.ir_cron_contract_daily_changes', raise_if_not_found=False)
    if cron:
        cron.unlink()
