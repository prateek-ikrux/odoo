# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    # Per stage and per report, so the stage a deal is meant to rest in - the
    # won stage, or any other the Admin adds - never flags anyone. Not keyed to
    # is_won: the Admin decides, and the upgrade only pre-unticks the won
    # stages.
    stage_reminders = fields.Boolean(
        string='Include in Stage Ageing Report',
        default=True,
        help="List active clients' opportunities that have remained in this "
             "stage for the days set in CRM settings in the weekly Stage "
             "Ageing Report.",
    )
    inactivity_reminders = fields.Boolean(
        string='Include in Client Inactivity Report',
        default=True,
        help="List active clients' opportunities in this stage with no "
             "recorded activity for the days set in CRM settings in the "
             "weekly Client Inactivity Report.",
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
