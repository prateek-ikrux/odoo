# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .contract import FEE_TYPE_SELECTION


class ContractFteConversion(models.TransientModel):
    """Convert an SOW's candidate into an FTE hire.

    For a client giving both kinds of business: the consultant placed on an
    SOW is hired by the client. The SOW is terminated as of the date of
    joining, and the candidate is recorded as an FTE placement under the same
    MSA - which has to do FTE as well as consulting - the two linked to each
    other. The fee starts from the MSA's standard FTE fee, where one is agreed.
    """
    _name = 'contracts.fte.conversion'
    _description = 'Convert an SOW to an FTE Placement'

    sow_id = fields.Many2one('contracts.contract', string='SOW', required=True, readonly=True)
    candidate = fields.Char(related='sow_id.candidate', string='Candidate Name')
    client = fields.Char(related='sow_id.client', string='Client')
    msa_id = fields.Many2one(related='sow_id.parent_contract_id', string='MSA')
    date_of_joining = fields.Date(
        string='DOJ', required=True, default=fields.Date.context_today,
        help="Date the candidate joins the client as an FTE. The SOW is "
             "terminated as of this date.",
    )
    skillset = fields.Char(string='Skillset')
    offered_ctc = fields.Float(string='Offered CTC', digits=(12, 2))
    fee_type = fields.Selection(FEE_TYPE_SELECTION, string='Claimed % or Flat Rate', required=True,
                                default='percentage')
    fee_value = fields.Float(string='Value', digits=(12, 2))
    billing_date = fields.Date(string='Billing Date')

    @api.constrains('offered_ctc', 'fee_type', 'fee_value')
    def _check_amounts(self):
        for rec in self:
            if rec.offered_ctc < 0 or rec.fee_value < 0:
                raise ValidationError(_("The Offered CTC and the Value cannot be negative."))
            if rec.fee_type == 'percentage' and rec.fee_value > 100:
                raise ValidationError(_("The claimed percentage cannot be more than 100."))

    def action_convert(self):
        self.ensure_one()
        sow = self.sow_id
        if sow.contract_type != 'sow' or sow.state == 'terminated':
            raise UserError(_("Only a running SOW can be converted to FTE."))
        if not sow.parent_contract_id._does_fte():
            raise UserError(_(
                "The MSA '%(msa)s' does not do FTE (%(type)s). Make it FTE/Consulting "
                "first, so the hire can be recorded under it.",
                msa=sow.parent_contract_id.display_name,
                type=sow.parent_contract_id._contract_type_label()))
        placement = self.env['contracts.fte.placement'].create({
            'msa_id': sow.parent_contract_id.id,
            'candidate': sow.candidate,
            'date_of_joining': self.date_of_joining,
            'skillset': self.skillset,
            'offered_ctc': self.offered_ctc,
            'fee_type': self.fee_type,
            'fee_value': self.fee_value,
            'billing_date': self.billing_date,
            'converted_from_sow_id': sow.id,
        })
        sow.write({'state': 'terminated', 'termination_date': self.date_of_joining})
        sow.message_post(
            body=Markup(_("Converted to FTE: %(candidate)s joins %(client)s as an FTE on "
                          "%(doj)s. Recorded as FTE placement %(link)s.")) % {
                'candidate': sow.candidate,
                'client': sow.client,
                'doj': self.date_of_joining.strftime('%d/%m/%Y'),
                'link': Markup('<a href="#" data-oe-model="contracts.fte.placement" '
                               'data-oe-id="%s">%s</a>') % (placement.id, placement.candidate),
            },
            subtype_xmlid='mail.mt_note',
        )
        placement.message_post(
            body=Markup(_("Converted from SOW %(link)s, terminated as of the date of joining.")) % {
                'link': Markup('<a href="#" data-oe-model="contracts.contract" '
                               'data-oe-id="%s">%s</a>') % (sow.id, sow.display_name),
            },
            subtype_xmlid='mail.mt_note',
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'contracts.fte.placement',
            'res_id': placement.id,
            'view_mode': 'form',
            'target': 'current',
        }
