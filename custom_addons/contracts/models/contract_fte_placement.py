# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .contract import FEE_TYPE_SELECTION


class ContractFtePlacement(models.Model):
    """A candidate hired by a client through an FTE MSA.

    The third section beside the MSA and the SOW. Not a contract of its own: it
    has no period, no state and no reminders, only the hire - who, when, on
    what CTC, and the fee claimed for it, billed on its own date - under the
    MSA it was made through, which has to be one doing FTE. The client is the
    MSA's, and so is the guarantee period the hire is covered by; the fee
    starts from the MSA's standard FTE fee, where one is agreed.

    Recorded directly, or by converting the candidate of an SOW under an
    FTE/Consulting MSA (contracts.fte.conversion), which ends the SOW.
    """
    _name = 'contracts.fte.placement'
    _inherit = ['mail.thread']
    _description = 'FTE Placement'
    _order = 'date_of_joining desc, id desc'
    _rec_name = 'candidate'
    _rec_names_search = ['candidate', 'client', 'skillset']

    msa_id = fields.Many2one(
        'contracts.contract', string='MSA', required=True, index=True,
        ondelete='restrict', tracking=True,
        # A terminated MSA is not offered for new hires. Not a constraint:
        # hires made before it was terminated stay valid, and an import of
        # past hires still has to be able to name it.
        domain="[('contract_type', '=', 'msa'), ('state', '!=', 'terminated'), "
               "('billing_mode', 'in', ('fte', 'both'))]",
        help="The FTE or FTE/Consulting MSA the candidate was hired through.",
    )
    candidate = fields.Char(string='Candidate Name', required=True, tracking=True)
    date_of_joining = fields.Date(
        string='DOJ', required=True, tracking=True,
        help="Date of joining: the day the candidate started with the client.",
    )
    skillset = fields.Char(string='Skillset', tracking=True)
    offered_ctc = fields.Float(
        string='Offered CTC', digits=(12, 2), tracking=True,
        help="The CTC the candidate was offered, as the full figure - e.g. "
             "1800000, not 18 lakhs.",
    )
    client = fields.Char(
        string='Client', related='msa_id.client', store=True, index=True,
    )
    fee_type = fields.Selection(
        FEE_TYPE_SELECTION, string='Claimed % or Flat Rate',
        required=True, tracking=True,
        compute='_compute_fee', store=True, readonly=False, precompute=True,
    )
    fee_value = fields.Float(
        string='Value', digits=(12, 2), tracking=True,
        compute='_compute_fee', store=True, readonly=False, precompute=True,
        help="The percentage claimed, e.g. 8.33 - or the flat rate, as the "
             "full figure. Starts from the MSA's standard FTE fee, where one "
             "is agreed.",
    )
    billing_date = fields.Date(
        string='Billing Date', tracking=True,
        help="The date this hire is billed on.",
    )
    converted_from_sow_id = fields.Many2one(
        'contracts.contract', string='Converted From', readonly=True,
        ondelete='set null', index=True,
        help="The SOW the candidate worked on before the client hired them, "
             "when the hire came from converting it.",
    )
    guarantee_period = fields.Selection(
        related='msa_id.guarantee_period', string='Guarantee Period',
    )
    guarantee_end_date = fields.Date(
        string='Guarantee Ends', compute='_compute_guarantee_end_date', store=True,
        help="Date of joining plus the MSA's guarantee period.",
    )

    @api.depends('msa_id')
    def _compute_fee(self):
        """Start from the standard FTE fee agreed on the MSA, where there is
        one. Only picking the MSA sets it: changing the MSA's standard fee
        later leaves the hires already made under it as they were."""
        for rec in self:
            msa = rec.msa_id
            if msa.fte_fee_type:
                rec.fee_type = msa.fte_fee_type
                rec.fee_value = msa.fte_fee_value
            else:
                rec.fee_type = rec.fee_type or 'percentage'
                rec.fee_value = rec.fee_value

    @api.depends('date_of_joining', 'msa_id.guarantee_period')
    def _compute_guarantee_end_date(self):
        for rec in self:
            period = rec.msa_id.guarantee_period
            rec.guarantee_end_date = fields.Date.add(rec.date_of_joining, days=int(period)) \
                if rec.date_of_joining and period else False

    @api.constrains('msa_id')
    def _check_msa(self):
        for rec in self:
            if rec.msa_id.contract_type != 'msa' or not rec.msa_id._does_fte():
                raise ValidationError(
                    _("FTE placement '%(name)s' has to be made through an FTE or "
                      "FTE/Consulting MSA; '%(msa)s' is not one (%(type)s).",
                      name=rec.candidate, msa=rec.msa_id.display_name,
                      type=rec.msa_id._contract_type_label())
                )

    @api.constrains('offered_ctc', 'fee_type', 'fee_value')
    def _check_amounts(self):
        for rec in self:
            if rec.offered_ctc < 0:
                raise ValidationError(
                    _("Offered CTC cannot be negative on FTE placement '%s'.", rec.candidate))
            if rec.fee_value < 0:
                raise ValidationError(
                    _("Value cannot be negative on FTE placement '%s'.", rec.candidate))
            if rec.fee_type == 'percentage' and rec.fee_value > 100:
                raise ValidationError(
                    _("The claimed percentage cannot be more than 100 on FTE "
                      "placement '%s'.", rec.candidate))

    def action_open_msa(self):
        """Open the MSA this hire was made through."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'contracts.contract',
            'res_id': self.msa_id.id,
            'view_mode': 'form',
            'views': [(self.env.ref('contracts.view_contracts_contract_form').id, 'form')],
        }
