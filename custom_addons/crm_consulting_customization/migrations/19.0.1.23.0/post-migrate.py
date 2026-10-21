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


POC_SUFFIXES = ('name', 'designation', 'phone', 'email', 'location', 'linkedin')


def migrate(cr, version):
    """POCs lose their limit, and stuck-in-stage reminders become one weekly
    report."""
    if not version:
        return
    move_fixed_pocs(cr)
    schedule_stage_report(cr)


def move_fixed_pocs(cr):
    """Move POC 2 to 5 off their fixed columns and into the POC list, in
    order, one row for every block that holds anything at all - a block with
    only a phone number is still a POC worth keeping.

    Runs before the upgrade drops the old columns, which the model no longer
    declares.
    """
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'crm_lead'")
    columns = {row[0] for row in cr.fetchall()}
    for n in (2, 3, 4, 5):
        block = ['poc%d_%s' % (n, suffix) for suffix in POC_SUFFIXES]
        if not set(block) <= columns:
            continue
        cr.execute("""
            INSERT INTO crm_lead_poc (lead_id, sequence, name, designation, phone,
                                      email, location, linkedin,
                                      create_uid, create_date, write_uid, write_date)
            SELECT id, %s, {0}, {1}, {2}, {3}, {4}, {5},
                   COALESCE(write_uid, create_uid), now() AT TIME ZONE 'UTC',
                   COALESCE(write_uid, create_uid), now() AT TIME ZONE 'UTC'
              FROM crm_lead
             WHERE {6}
             ORDER BY id
        """.format(*block, ' OR '.join(
            "COALESCE(TRIM(%s), '') <> ''" % column for column in block)), (n * 10,))


def schedule_stage_report(cr):
    """The stuck-in-stage job is noupdate data, so the upgrade alone would
    leave it calling the old daily method. It is pointed at the report and at
    the next midnight starting the picked weekday (Monday unless set), in the
    Admin's timezone; saving CRM settings later moves it to the saver's.
    """
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
