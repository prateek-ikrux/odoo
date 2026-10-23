# -*- coding: utf-8 -*-
from odoo import api, fields, models


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

    # A change here reaches the opportunity's audit log and change
    # notification through its POC List (crm.lead.poc_summary). Each starts
    # tracking that list as whoever makes it, before it is made: left to the
    # recompute at the save, the change would be put down to whichever user
    # the save runs as, and could read as an automatic one.
    @api.model_create_multi
    def create(self, vals_list):
        self.env['crm.lead'].browse(
            {vals['lead_id'] for vals in vals_list if vals.get('lead_id')})._track_poc_change()
        return super().create(vals_list)

    def write(self, vals):
        leads = self.lead_id
        if vals.get('lead_id'):
            leads |= self.env['crm.lead'].browse(vals['lead_id'])
        leads._track_poc_change()
        return super().write(vals)

    def unlink(self):
        self.lead_id._track_poc_change()
        return super().unlink()
