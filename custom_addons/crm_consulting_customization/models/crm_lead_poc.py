# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmLeadPoc(models.Model):
    """A POC on an opportunity - as many as it needs, the first of them the
    primary contact, whose details the opportunity keeps a copy of.

    Name, Designation and Location are asked for by the form rather than
    required here, so an import or an older record holding only a phone
    number still loads.
    """
    _name = 'crm.lead.poc'
    _description = 'Opportunity POC'
    _order = 'lead_id, sequence, id'
    _rec_name = 'name'

    lead_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True, index=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char('POC Name')
    designation = fields.Char('Designation')
    phone = fields.Char('Phone Number')
    email = fields.Char('Email')
    location = fields.Char('Location')
    linkedin = fields.Char('LinkedIn')
