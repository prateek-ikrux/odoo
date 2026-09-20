# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmLeadLost(models.TransientModel):
    """Closed-lost is a status carrying a reason, not a pipeline stage.

    CRM ships the wizard with an optional reason, which lets an opportunity be
    marked lost with nothing recorded about why. Making it required is what
    turns the closed-lost analysis report into something worth reading.
    """
    _inherit = 'crm.lead.lost'

    lost_reason_id = fields.Many2one(required=True)
