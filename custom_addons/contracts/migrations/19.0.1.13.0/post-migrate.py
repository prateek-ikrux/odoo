# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api
from odoo.tools.mail import email_normalize

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Move the expiry reminder recipients from typed addresses to users.

    Each address is matched to the internal user carrying it and added to the
    new picker. An address with no such user cannot be carried over - the
    picker only holds users - so it is named in the log rather than dropped
    without a trace. The old parameter goes either way: nothing reads it now.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    param = env['ir.config_parameter'].search([('key', '=', 'contracts.reminder_emails')])
    if not param:
        return
    Users = env['res.users'].with_context(active_test=False)
    matched, unmatched = Users, []
    for token in (param.value or '').split(','):
        email = email_normalize(token.strip())
        if not email:
            continue
        user = Users.search([('share', '=', False), ('email_normalized', '=', email)], limit=1)
        if user:
            matched |= user
        else:
            unmatched.append(email)
    if matched:
        for company in env['res.company'].search([]):
            company.contracts_reminder_recipient_ids |= matched
    if unmatched:
        _logger.warning(
            "Contracts: expiry reminder recipients %s match no internal user and "
            "were not carried over; create users for them and pick them under "
            "Contracts > Configuration > Settings.", ', '.join(unmatched))
    param.unlink()
