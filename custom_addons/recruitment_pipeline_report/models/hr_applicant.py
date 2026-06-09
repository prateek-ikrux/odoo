# -*- coding: utf-8 -*-
from odoo import models, fields


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # Job-position attributes — readonly mirrors from the linked job
    x_role_status = fields.Selection(
        related='job_id.x_role_status',
        string='Role Status',
        store=True,
        readonly=True,
    )

    x_sub_status = fields.Selection(
        related='job_id.x_sub_status',
        string='Sub Status',
        store=True,
        readonly=True,
    )

    x_employment_type = fields.Selection(
        related='job_id.x_employment_type',
        string='Employment Type',
        store=True,
        readonly=True,
    )

    x_poc_id = fields.Many2one(
        related='job_id.x_poc_id',
        string='POC',
        store=True,
        readonly=True,
    )

    x_no_of_positions = fields.Integer(
        related='job_id.no_of_recruitment',
        string='No. of Positions',
        store=True,
        readonly=True,
    )
