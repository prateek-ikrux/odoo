# -*- coding: utf-8 -*-
from odoo import models, fields

class RecruitmentCity(models.Model):
    _name = 'recruitment.city'
    _description = 'City Master'
    _order = 'name'

    name = fields.Char(string='City Name', required=True)

    _name_uniq = models.Constraint(
        'unique (name)',
        'City name must be unique!',
    )
