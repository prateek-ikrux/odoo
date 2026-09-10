# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RecruiterTeam(models.Model):
    _name = 'recruiter.team'
    _description = 'Recruiter Group'
    _order = 'name'

    name = fields.Char(string='Group Name', required=True)

    member_ids = fields.Many2many(
        'res.users',
        'recruiter_team_member_rel',
        'team_id', 'user_id',
        string='Members',
        domain="[('share', '=', False)]",
        required=True,
    )

    team_lead_id = fields.Many2one(
        'res.users',
        string='Team Lead',
        domain="[('id', 'in', member_ids)]",
        required=True,
        help='Must be one of the selected Members. This person is set as the '
             'job position\'s Recruitment Manager whenever this group is applied.',
    )

    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        'unique (name)',
        'A recruiter group with this name already exists!',
    )

    @api.constrains('team_lead_id', 'member_ids')
    def _check_team_lead_is_member(self):
        for rec in self:
            if rec.team_lead_id and rec.team_lead_id not in rec.member_ids:
                raise ValidationError(
                    'Team Lead must be one of the selected Members.'
                )

    @api.onchange('member_ids')
    def _onchange_member_ids(self):
        # Keep team_lead_id valid if members are removed
        if self.team_lead_id and self.team_lead_id not in self.member_ids:
            self.team_lead_id = False
