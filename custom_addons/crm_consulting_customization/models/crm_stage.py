# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    # Per stage, so the stage a deal is meant to rest in - the won stage, or
    # any other the Admin adds - never nags anyone. Not keyed to is_won: the
    # Admin decides, and the upgrade only pre-unticks the won stages.
    stage_reminders = fields.Boolean(
        string='Send Stuck-in-Stage Reminders',
        default=True,
        help="Email a reminder when an active client's opportunity stays in "
             "this stage longer than the days set in CRM settings.",
    )
