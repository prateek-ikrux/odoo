# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from odoo.addons.recruitment_pipeline_report import setup_notification_defaults


def migrate(cr, version):
    """Email notifications arrive on an existing database: outcome stages
    start with stuck reminders off, and every candidate's Entered Stage On is
    filled in from their stage history. The emails themselves start switched
    off, so nothing is sent until they are turned on in the settings."""
    if not version:
        return
    setup_notification_defaults(api.Environment(cr, SUPERUSER_ID, {}))
