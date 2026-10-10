# -*- coding: utf-8 -*-
from odoo import fields, models


class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'

    # Per stage, so outcome stages - rejected, joined, declined - never nag
    # anyone about a candidate who is meant to stay there.
    x_stage_reminders = fields.Boolean(
        string='Send Stuck-Candidate Reminders',
        default=True,
        help="Email a reminder when a candidate stays in this stage longer "
             "than the days set in Recruitment settings.",
    )
