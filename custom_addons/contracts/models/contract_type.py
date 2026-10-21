# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# How business is done under a contract of this type. FTE is billed on the
# overarching contract itself; consulting is billed on each Statement of Work
# placed under it; a type doing both does each, in its own place.
BILLING_MODE_SELECTION = [
    ('fte', 'FTE'),
    ('consulting', 'Consulting'),
    ('both', 'FTE & Consulting'),
]
FTE_MODES = ('fte', 'both')
CONSULTING_MODES = ('consulting', 'both')


class ContractTypeMaster(models.Model):
    """Master list of contract types, kept under Configuration.

    Not to be confused with ``contracts.contract.contract_type``, the hidden
    MSA / SOW discriminator: this is the business classification picked on an
    overarching contract, which also decides how that contract is billed. A
    placed contract has none: it is always a consulting placement, billed on
    its own, under the contract above it.
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
    billing_mode = fields.Selection(
        BILLING_MODE_SELECTION, string='Billing Mode',
        required=True, default='consulting',
        help="FTE: billed on the Master Service Agreement, by bill rate.\n"
             "Consulting: billed on each Statement of Work under it, by budget; "
             "only these take Statements of Work.\n"
             "FTE & Consulting: both - FTE billed on the Master Service "
             "Agreement, consulting on each Statement of Work under it.",
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

    @api.constrains('billing_mode')
    def _check_billing_mode(self):
        """Moving a type to FTE alone cannot strand SOWs already placed
        under its contracts: FTE takes none."""
        for rec in self.filtered(lambda t: t.billing_mode == 'fte'):
            used = self.env['contracts.contract'].search_count([
                ('contract_type', '=', 'sow'),
                ('parent_contract_id.type_id', '=', rec.id),
            ], limit=1)
            if used:
                raise ValidationError(
                    _("Contract type '%s' still has Statements of Work placed "
                      "under its contracts, so it has to keep Consulting.",
                      rec.name)
                )

    def write(self, vals):
        res = super().write(vals)
        if 'billing_mode' in vals:
            # Contracts of a type moved off FTE stop showing their bill rate;
            # wipe it, as moving a single contract to such a type would.
            self.env['contracts.contract'].search([
                ('contract_type', '=', 'msa'), ('type_id', 'in', self.ids),
            ])._clear_unused_billing()
        return res
