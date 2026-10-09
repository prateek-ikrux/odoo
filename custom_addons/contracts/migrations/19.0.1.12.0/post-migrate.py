# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Keep everyone's access as it was before Contracts had its own groups.

    Until now every internal user could use Contracts and system admins could
    also delete contracts and maintain the master list. Access is now granted
    per user, so the users who had it are given the matching group - after
    which it can be taken away from the user form.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Users = env['res.users'].with_context(active_test=False)
    internal = Users.search([('share', '=', False)])
    env.ref('contracts.group_contracts_user').write(
        {'user_ids': [(4, uid) for uid in internal.ids]})
    admins = Users.search([('all_group_ids', 'in', env.ref('base.group_system').id)])
    env.ref('contracts.group_contracts_manager').write(
        {'user_ids': [(4, uid) for uid in admins.ids]})
