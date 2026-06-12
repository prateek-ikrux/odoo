from odoo import models, fields

class HrApplicantOfferTag(models.Model):
    _name = 'hr.applicant.offer.tag'
    _description = 'Offer in Hand Tag'
    
    name = fields.Char(string='Offer Amount (LPA)', required=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Tag name already exists!')
    ]
