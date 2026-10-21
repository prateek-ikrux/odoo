# -*- coding: utf-8 -*-
from odoo import _, fields, models


class CrmClassificationMixin(models.AbstractModel):
    """A master list an opportunity is classified against.

    Client Type and Industry / Domain are the same thing twice: a short list
    the Sales Manager keeps under CRM > Configuration, and an opportunity picks
    one entry from. Each concrete list names the crm.lead field that points at
    it in _lead_field, which is all the opportunity count needs to know.

    An entry that is in use cannot be deleted - the opportunity field is
    ondelete='restrict' - so a report never loses a bucket it was grouping by.
    Archiving takes it off the dropdown and leaves the opportunities on it
    alone.
    """
    _name = 'crm.classification.mixin'
    _description = 'Opportunity Classification List'
    _order = 'sequence, name, id'

    _lead_field = None

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    lead_count = fields.Integer('Opportunities', compute='_compute_lead_count')

    def _compute_lead_count(self):
        counts = dict(self.env['crm.lead'].with_context(active_test=False)._read_group(
            [(self._lead_field, 'in', self.ids)],
            [self._lead_field],
            ['__count'],
        ))
        for record in self:
            record.lead_count = counts.get(record, 0)

    def action_view_leads(self):
        self.ensure_one()
        return {
            'name': _('Opportunities'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [(self._lead_field, '=', self.id)],
            'context': {'create': False, 'active_test': False},
        }


class CrmClientType(models.Model):
    _name = 'crm.client.type'
    _inherit = 'crm.classification.mixin'
    _description = 'Client Type'

    _lead_field = 'client_type'

    # Two entries with one name would split a report into two buckets that
    # read the same.
    _name_unique = models.Constraint(
        'unique(name)',
        'This name is already on the list.',
    )


class CrmIndustryDomain(models.Model):
    _name = 'crm.industry.domain'
    _inherit = 'crm.classification.mixin'
    _description = 'Industry / Domain'

    _lead_field = 'industry_domain'

    # Two entries with one name would split a report into two buckets that
    # read the same.
    _name_unique = models.Constraint(
        'unique(name)',
        'This name is already on the list.',
    )
