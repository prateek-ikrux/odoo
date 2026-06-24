from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

# Plain integer or decimal only (e.g. "12", "12.5"). Deliberately stricter
# than Python's float() to reject scientific notation ("1e5"), "inf"/"nan",
# and other oddities that float() would otherwise silently accept.
_NUMERIC_RE = re.compile(r'^\d+(\.\d+)?$')


class HrApplicantOfferTag(models.Model):
    _name = 'hr.applicant.offer.tag'
    _description = 'Offer in Hand Tag'

    name = fields.Char(string='Offer Amount (LPA)', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Tag name already exists!')
    ]

    @api.constrains('name')
    def _check_name_is_float(self):
        for rec in self:
            if not rec.name or not _NUMERIC_RE.match(rec.name.strip()):
                raise ValidationError(
                    'Offer in Hand (LPA) "%s" is not valid. Please enter a number, '
                    'e.g. 12 or 12.5.' % rec.name
                )
