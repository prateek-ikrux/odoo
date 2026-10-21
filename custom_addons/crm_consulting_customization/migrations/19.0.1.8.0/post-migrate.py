# -*- coding: utf-8 -*-
"""Undo what this module did to records it did not own.

Removing the roles and the reports takes this module's own records with it -
Odoo deletes an external id that no data file claims any more. Three things do
not go that way, and each has to be undone by hand:

* Two record rules that belong to `crm`. This module rewrote them in place
  rather than adding its own, because record rules from different groups are
  OR-ed and a second rule could only ever widen what a salesperson sees.
  Rewriting was the only way to narrow it. Both are flagged no-update in `crm`,
  which is what kept this module's version safe from a `crm` upgrade - and what
  stops a `crm` upgrade putting the originals back now.

* Two `crm` actions whose context this module rewrote, to stop the pipeline
  opening pre-filtered to the user's own opportunities. Those are not no-update,
  but `crm` only reapplies its own data when `crm` itself is upgraded, so they
  would sit rewritten until that happened.

* This module's ageing cron, which *is* its own but is flagged no-update, and
  stale no-update records are left alone rather than deleted. It would survive
  into a database whose crm.lead no longer has the method it calls, and fail
  every night.

The domains and contexts below are Odoo 19.0's, copied from
crm/security/crm_security.xml and crm/views/crm_lead_views.xml.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

ORIGINAL_DOMAINS = {
    'crm.crm_rule_personal_lead':
        "['|',('user_id','=',user.id),('user_id','=',False)]",
    'crm.crm_activity_report_rule_personal_activities':
        "['|',('user_id','=',user.id),('user_id','=',False)]",
}

ORIGINAL_CONTEXTS = {
    'crm.crm_lead_action_pipeline': (
        "{\n"
        "                    'default_type': 'opportunity',\n"
        "                    'search_default_assigned_to_me': 1,\n"
        "                    'show_user_team_stages': 1,\n"
        "            }"
    ),
    'crm.crm_lead_action_forecast': (
        "{\n"
        "                'default_type': 'opportunity',\n"
        "                'search_default_assigned_to_me': 1,\n"
        "                'search_default_forecast': 1,\n"
        "                'search_default_date_deadline': 1,\n"
        "                'forecast_field': 'date_deadline'\n"
        "            }"
    ),
}

OWN_NO_UPDATE_RECORDS = ['crm_consulting_customization.ir_cron_refresh_stage_ageing']


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    for xmlid, domain in ORIGINAL_DOMAINS.items():
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule and rule.domain_force != domain:
            _logger.info(
                "crm_consulting_customization: restoring CRM's own domain on %s (was %s)",
                xmlid, rule.domain_force,
            )
            rule.domain_force = domain

    for xmlid, context in ORIGINAL_CONTEXTS.items():
        action = env.ref(xmlid, raise_if_not_found=False)
        if action and action.context != context:
            _logger.info(
                "crm_consulting_customization: restoring CRM's own context on %s", xmlid)
            action.context = context

    for xmlid in OWN_NO_UPDATE_RECORDS:
        record = env.ref(xmlid, raise_if_not_found=False)
        if not record:
            continue
        _logger.info(
            "crm_consulting_customization: deleting %s; it is flagged no-update, so "
            "the upgrade leaves it behind", xmlid)
        # An ir.cron delegates to an ir.actions.server, and deleting the cron
        # does not take the server action with it. Left alone it stays in
        # Settings > Technical > Server Actions, detached from any schedule but
        # still offering to run `model._cron_refresh_stage_ageing()`, which this
        # version of crm.lead no longer defines.
        server_action = record.ir_actions_server_id
        record.unlink()
        if server_action.exists():
            server_action.unlink()

    # An external id whose record is gone is dead weight; Odoo keeps the row.
    stale = env['ir.model.data'].search([
        ('module', '=', 'crm_consulting_customization'),
    ]).filtered(lambda d: d.model not in env or not env[d.model].browse(d.res_id).exists())
    if stale:
        _logger.info("crm_consulting_customization: dropping %d stale external ids", len(stale))
        stale.unlink()
