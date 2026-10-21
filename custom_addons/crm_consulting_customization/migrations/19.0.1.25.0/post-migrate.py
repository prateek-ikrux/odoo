# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

# The per-kind ticks the notification hierarchy replaces: BDAs, their team
# leaders, the activity's assignee and the upward-only filter.
STALE_PARAMS = (
    'crm_consulting.change_notify_bda',
    'crm_consulting.change_notify_bda_leader',
    'crm_consulting.change_notify_upward',
    'crm_consulting.activity_reminders_bda',
    'crm_consulting.activity_reminders_bda_leader',
    'crm_consulting.activity_reminders_assignee',
)

# Reminders go to the assignee and up the hierarchy unless switched off.
REMINDER_TICKS = (
    'crm_consulting.activity_reminders_team_leader',
    'crm_consulting.activity_reminders_leadership',
)


def migrate(cr, version):
    """Change notifications and activity reminders follow one hierarchy.

    The change notification list was where leadership was picked, so whoever
    is on it becomes Leadership. The activity reminder list has no place in
    the hierarchy and is dropped with its field. Odoo removes both fields
    after this script but leaves their relation tables in place; nothing
    reads them any more.
    """
    if not version:
        return
    cr.execute("SELECT to_regclass('crm_change_recipient_rel')")
    if cr.fetchone()[0]:
        cr.execute("""
            INSERT INTO crm_leadership_rel (company_id, user_id)
            SELECT company_id, user_id FROM crm_change_recipient_rel
            ON CONFLICT DO NOTHING
        """)
    env = api.Environment(cr, SUPERUSER_ID, {})
    params = env['ir.config_parameter'].sudo()
    params.search([('key', 'in', STALE_PARAMS)]).unlink()
    for key in REMINDER_TICKS:
        if params._get_param(key) is None:
            params.set_param(key, True)
