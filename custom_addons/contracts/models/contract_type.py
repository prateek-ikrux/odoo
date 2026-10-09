# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ContractTypeMaster(models.Model):
    """Master list of contract types, kept under Configuration.

    Not to be confused with ``contracts.contract.contract_type``, the hidden
    MSA / SOW discriminator: this is the business classification picked on an
    overarching contract. A placed contract has none: SOWs only ever sit
    under MSAs whose type allows them, so the type would say nothing.
    """
    _name = 'contracts.type'
    _description = 'Contract Type'
    _order = 'sequence, name, id'

    name = fields.Char(string='Contract Type', required=True)
    sequence = fields.Integer(default=10)
    # Archived rather than deleted once in use: contracts keep the type they
    # were recorded with, it just stops being offered for new ones.
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')
    allows_sow = fields.Boolean(
        string='Allows SOWs',
        help="Statements of Work can only be placed under a Master Service "
             "Agreement whose type has this ticked.",
    )
    contract_count = fields.Integer(
        string='# Contracts', compute='_compute_contract_count',
    )

    _name_uniq = models.Constraint(
        'unique (name)',
        "A contract type with this name already exists.",
    )

    def _compute_contract_count(self):
        counts = dict(self.env['contracts.contract']._read_group(
            [('type_id', 'in', self.ids)], ['type_id'], ['__count'],
        ))
        for rec in self:
            rec.contract_count = counts.get(rec, 0)

    @api.constrains('allows_sow')
    def _check_allows_sow(self):
        """Unticking cannot strand SOWs already placed under this type."""
        for rec in self.filtered(lambda t: not t.allows_sow):
            used = self.env['contracts.contract'].search_count([
                ('contract_type', '=', 'sow'),
                ('parent_contract_id.type_id', '=', rec.id),
            ], limit=1)
            if used:
                raise ValidationError(
                    _("Contract type '%s' still has Statements of Work placed "
                      "under its contracts, so it has to keep allowing them.",
                      rec.name)
                )
