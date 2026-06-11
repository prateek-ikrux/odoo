# -*- coding: utf-8 -*-
from odoo import models, fields

class RecruitmentSkill(models.Model):
    _name = 'recruitment.skill'
    _description = 'Skill Master'
    _order = 'name'

    name = fields.Char(string='Skill Name', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Skill name must be unique!')
    ]
