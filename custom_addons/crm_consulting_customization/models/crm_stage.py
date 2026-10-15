# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    # Per stage, so the stage a deal is meant to rest in - the won stage, or
    # any other the Admin adds - never nags anyone. Not keyed to is_won: the
    # Admin decides, and the upgrade only pre-unticks the won stages.
    stage_reminders = fields.Boolean(
        string='Include in Stuck-in-Stage Report',
        default=True,
        help="List active clients' opportunities that sit in this stage longer "
             "than the days set in CRM settings in the weekly stuck-in-stage "
             "report.",
    )

    @api.onchange('is_won')
    def _onchange_is_won(self):
        """Warn about recomputing probabilities only when there are some.

        CRM warns that every opportunity in the stage will have its
        probability recomputed on saving. A stage with none in it - one just
        added, say - has nothing to recompute, and the warning only alarms.
        """
        # sudo: counting only, so the check does not depend on who can see
        # which opportunities.
        if not self._origin or not self.env['crm.lead'].sudo().search_count(
                [('stage_id', '=', self._origin.id)], limit=1):
            return None
        return super()._onchange_is_won()
