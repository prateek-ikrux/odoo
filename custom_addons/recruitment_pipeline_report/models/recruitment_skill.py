# -*- coding: utf-8 -*-
from odoo import models, fields

class RecruitmentSkill(models.Model):
    _name = 'recruitment.skill'
    _description = 'Skill Master'
    _order = 'name'

    name = fields.Char(string='Skill Name', required=True)

    _name_uniq = models.Constraint(
        'unique (name)',
        'Skill name must be unique!',
    )
