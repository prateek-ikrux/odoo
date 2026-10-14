# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from odoo.addons.crm_consulting_customization.models.crm_lead import (
    STAGE_REPORT_TZ_PARAM, STAGE_REPORT_WEEKDAY_PARAM,
)

# The day marks of the per-opportunity reminders this replaces, and two
# frequencies an earlier, abandoned build of a report left behind.
STALE_PARAMS = (
    'crm_consulting.stage_reminder_days',
    'crm_consulting.stage_report_frequency',
    'crm_consulting.change_report_frequency',
)


def migrate(cr, version):
    """Stuck-in-stage reminders become one weekly report.

    The job is noupdate data, so the upgrade alone would leave it calling the
    old daily method. It is pointed at the report and at the next midnight
    starting the picked weekday (Monday unless set), in the Admin's timezone;
    saving CRM settings later moves it to the saver's.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    params = env['ir.config_parameter'].sudo()
    params.search([('key', 'in', STALE_PARAMS)]).unlink()
    cron = env.ref('crm_consulting_customization.ir_cron_crm_stage_reminders',
                   raise_if_not_found=False)
    if not cron:
        return
    tz_name = params.get_param(STAGE_REPORT_TZ_PARAM) or env.ref('base.user_admin').tz or 'UTC'
    params.set_param(STAGE_REPORT_TZ_PARAM, tz_name)
    weekday = params.get_param(STAGE_REPORT_WEEKDAY_PARAM) or '0'
    cron.write({
        'name': 'CRM: Stuck-in-Stage Report',
        'code': 'model._cron_send_stage_report()',
        'interval_number': 1,
        'interval_type': 'weeks',
        'nextcall': env['res.config.settings']._crm_next_report_call(
            int(weekday), tz_name, env.cr.now()),
    })
