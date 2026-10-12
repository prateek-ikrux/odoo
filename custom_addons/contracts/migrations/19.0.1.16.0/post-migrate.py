# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

# Left behind by 19.0.1.15.0 as first built - the scheduled Excel reports -
# whose code is gone. Their jobs would fail on every run.
STALE_CRONS = (
    'contracts.ir_cron_contract_expiry_report',
    'contracts.ir_cron_contract_change_report',
)
STALE_PARAMS = (
    'contracts.expiry_report', 'contracts.expiry_report_frequency',
    'contracts.expiry_report_days', 'contracts.expiry_report_last_sent',
    'contracts.change_report_frequency', 'contracts.change_report_last_sent',
)


def migrate(cr, version):
    """Change notifications become one email at the end of the day; clear out
    what the earlier report-based build of the same version left behind."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in STALE_CRONS:
        cron = env.ref(xmlid, raise_if_not_found=False)
        if cron:
            cron.unlink()
    env['ir.config_parameter'].sudo().search([('key', 'in', STALE_PARAMS)]).unlink()
