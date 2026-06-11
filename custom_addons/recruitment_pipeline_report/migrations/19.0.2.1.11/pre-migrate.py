# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    env = env(context=dict(env.context, lang='en_US'))

    renames = {
        'Client Round': 'L3',
        'Client Round TBS': 'L3 TBS',
        'Client Round Slot Shared': 'L3 Slot Shared',
        'Client Round Scheduled': 'L3 Scheduled',
        'Client Round Feedback Pending': 'L3 Feedback Pending',
        'Client Round Reject': 'L3 Reject',
        'TBO': 'To Be Offered',
    }

    for old_name, new_name in renames.items():
        stages = env['hr.recruitment.stage'].search([('name', '=', old_name)])
        for stage in stages:
            stage.name = new_name
