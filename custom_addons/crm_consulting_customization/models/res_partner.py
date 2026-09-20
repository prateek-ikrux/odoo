# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # City or site the company operates from, or the POC sits at. Separate
    # from the address block's own city, which belongs to the postal address
    # and cannot hold a site name.
    location = fields.Char(
        'Location',
        help='City or site.',
    )

    # The company record holds the LinkedIn page and the POC record the
    # POC's own LinkedIn profile. Relabelled rather than replaced, so the
    # url widget, the existing data and anything already reading website all
    # keep working.
    website = fields.Char(string='LinkedIn')

    # Relabelled for the same reason: function is the field every other Odoo
    # view already calls the job position, and the business calls it the
    # designation.
    function = fields.Char(string='Designation')
