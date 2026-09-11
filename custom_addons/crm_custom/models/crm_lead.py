# -*- coding: utf-8 -*-
from odoo import api, fields, models

YES_NO_SELECTION = [('no', 'No'), ('yes', 'Yes')]


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # The company behind a lead is always the client we staff for, so the core
    # "Company Name" field is relabelled rather than duplicated.
    partner_name = fields.Char(string='Client Name')

    # Optional by design: the percentage is rarely known when the lead is first
    # raised, so nothing here is required and 0 reads as "not discussed yet".
    x_percentage_discussed = fields.Float(
        string='Percentage Discussed',
        digits=(5, 2),
        tracking=True,
        help='Percentage agreed with the client on a full-time placement. '
             'Shown in the title in place of the expected revenue and the win '
             'probability. Leave at 0 until it has been discussed.',
    )

    # The consulting counterpart of the percentage: one or the other applies,
    # never both, so the form shows whichever matches the engagement type.
    x_bill_rate = fields.Monetary(
        string='Bill Rate',
        currency_field='company_currency',
        tracking=True,
        help='Rate billed to the client on a consulting engagement. '
             'Leave at 0 until it has been discussed.',
    )

    x_client_location = fields.Char(
        string='Client Location',
        tracking=True,
        help='Location the client company operates from, where a full postal '
             'address is more detail than the deal needs.',
    )

    x_poc_location = fields.Char(
        string='POC Location',
        tracking=True,
        help='Location the client point of contact operates from.',
    )

    x_client_type = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('dormant', 'Dormant'),
            ('passive', 'Passive'),
        ],
        string='Type of Client',
        tracking=True,
    )

    x_open_positions = fields.Integer(
        string='No. of Open Positions',
        tracking=True,
        help='Total headcount the client is hiring for.',
    )

    x_roles_opened = fields.Integer(
        string='Roles Opened',
        tracking=True,
        help='Number of distinct roles opened, which may be fewer than the '
             'number of open positions.',
    )

    x_engagement_type = fields.Selection(
        selection=[
            ('full_time', 'Full-time'),
            # Relabelled from "Contract"; the key is left alone so stored leads
            # and the view modifiers reading it do not need migrating.
            ('contract', 'Consulting'),
        ],
        string='Engagement Type',
        default='contract',
        tracking=True,
        help='A full-time hire has no project duration, so the duration reads NA. '
             'Full-time carries the percentage discussed, consulting the bill rate.',
    )

    x_project_duration_months = fields.Integer(
        string='Project Duration (Months)',
        tracking=True,
    )

    x_project_duration = fields.Char(
        string='Duration of the Project',
        compute='_compute_x_project_duration',
        store=True,
        help='NA for a full-time engagement, otherwise the duration in months.',
    )

    x_requirement_received = fields.Selection(
        selection=YES_NO_SELECTION,
        string='Requirement Received',
        default='no',
        tracking=True,
    )

    x_recruitment_started = fields.Selection(
        selection=YES_NO_SELECTION,
        string='Recruitment Started',
        default='no',
        tracking=True,
    )

    x_agreement_signed = fields.Selection(
        selection=YES_NO_SELECTION,
        string='Agreement Signed',
        default='no',
        tracking=True,
    )

    x_client_onboarded = fields.Selection(
        selection=YES_NO_SELECTION,
        string='Client Onboarded',
        default='no',
        tracking=True,
    )

    @api.depends('x_engagement_type', 'x_project_duration_months')
    def _compute_x_project_duration(self):
        for lead in self:
            if lead.x_engagement_type == 'full_time':
                lead.x_project_duration = 'NA'
            elif lead.x_project_duration_months:
                months = lead.x_project_duration_months
                lead.x_project_duration = '%s month%s' % (months, '' if months == 1 else 's')
            else:
                lead.x_project_duration = False

    @api.onchange('x_engagement_type')
    def _onchange_x_engagement_type(self):
        # A full-time engagement has no duration to carry over.
        if self.x_engagement_type == 'full_time':
            self.x_project_duration_months = 0
