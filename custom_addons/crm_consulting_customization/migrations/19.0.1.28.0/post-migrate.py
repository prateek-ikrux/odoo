# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from odoo.addons.crm_consulting_customization.models.crm_lead import STAGE_REPORT_TZ_PARAM


def migrate(cr, version):
    """The stuck-in-stage report becomes the Stage Ageing Report, the Client
    Inactivity Report joins it, and both take a schedule of their own.

    Both jobs are noupdate data, so they are set up here: each now runs
    daily at the report's time of day and sends only on the days its
    frequency names. Nothing set yet means weekly on the weekday already
    picked, at midnight - what the old report did - in the timezone the
    reports already use.

    The won stage is where a deal is meant to rest, so it starts out of the
    new report as it did of the old one.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['crm.stage'].search([('is_won', '=', True)]).write({'inactivity_reminders': False})

    params = env['ir.config_parameter'].sudo()
    tz_name = params.get_param(STAGE_REPORT_TZ_PARAM) or env.ref('base.user_admin').tz or 'UTC'
    nextcall = env['res.config.settings']._crm_next_daily_call(0.0, tz_name, env.cr.now())
    for xmlid, name in (('ir_cron_crm_stage_reminders', 'CRM: Stage Ageing Report'),
                        ('ir_cron_crm_inactivity_report', 'CRM: Client Inactivity Report')):
        cron = env.ref(f'crm_consulting_customization.{xmlid}', raise_if_not_found=False)
        if cron:
            cron.write({'name': name, 'interval_number': 1, 'interval_type': 'days',
                        'nextcall': nextcall})
