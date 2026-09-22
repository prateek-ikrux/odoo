# -*- coding: utf-8 -*-
from odoo import api, models


class ResGroups(models.Model):
    _inherit = 'res.groups'

    # Privileges whose dropdown on the user form is decided by another
    # privilege and must not be typed into directly. Sales is here because
    # every CRM role implies the sales_team group that goes with it, so the
    # Sales dropdown already shows the right answer - leaving it editable only
    # offers a way to disagree with the role, and the pair silently disagreeing
    # is exactly the bug this closes.
    READONLY_PRIVILEGE_XMLIDS = ['sales_team.res_groups_privilege_sales']

    @api.model
    def _get_view_group_hierarchy(self):
        """Mark the driven privileges read-only for the user form's widget.

        The Access Rights page is not an ordinary view - `res_user_group_ids`
        builds one selection field per privilege in the browser out of this
        dictionary, so there is no arch to put a readonly modifier on. The flag
        travels in the dictionary instead, and the widget patched in
        static/src/res_user_group_ids_field.js turns it into readonly="1" on
        the field it generates.
        """
        hierarchy = super()._get_view_group_hierarchy()

        xmlid_to_res_id = self.env['ir.model.data']._xmlid_to_res_id
        readonly_ids = [
            privilege_id
            for privilege_id in (
                xmlid_to_res_id(xmlid, raise_if_not_found=False)
                for xmlid in self.READONLY_PRIVILEGE_XMLIDS
            )
            if privilege_id and privilege_id in hierarchy['privileges']
        ]
        if not readonly_ids:
            return hierarchy

        # super() memoises its return value and hands out the same object every
        # time, so the flag goes onto copies. Writing it in place would work
        # today and would be a trap the first time anything else wants to edit
        # this dictionary per-user.
        privileges = dict(hierarchy['privileges'])
        for privilege_id in readonly_ids:
            privileges[privilege_id] = dict(privileges[privilege_id], readonly=True)
        return dict(hierarchy, privileges=privileges)
