# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from odoo.addons.crm_consulting_customization import setup_notification_defaults


def migrate(cr, version):
    """Starting values for the email notifications on an existing database:
    no stuck-in-stage reminders from the won stage, and activity reminders
    for calls and meetings. Every notification itself starts switched off,
    so nothing is sent until it is turned on in the settings."""
    if not version:
        return
    setup_notification_defaults(api.Environment(cr, SUPERUSER_ID, {}))
