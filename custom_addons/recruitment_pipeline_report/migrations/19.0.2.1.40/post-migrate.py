# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

# The ticks that sent every kind of email to the record's creator and its
# assigned people, which used to start ticked.
CREATOR_ASSIGNED_PARAMS = tuple(
    'recruitment_pipeline.%s_notify_%s' % (kind, who)
    for kind in ('client', 'role', 'stuck')
    for who in ('creator', 'assigned')
)


def migrate(cr, version):
    """Nobody receives a recruitment email unless picked. The creator and
    assigned ticks are switched off - a missing parameter reads as unticked -
    and can be ticked again under Recruitment > Configuration > Settings."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.config_parameter'].sudo().search([('key', 'in', CREATOR_ASSIGNED_PARAMS)]).unlink()
