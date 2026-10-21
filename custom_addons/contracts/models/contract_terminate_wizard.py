# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ContractTerminateConfirm(models.TransientModel):
    _name = 'contracts.terminate.confirm'
    _description = 'Contract Termination Confirmation'

    contract_id = fields.Many2one(
        'contracts.contract', string='Contract', required=True, ondelete='cascade',
    )
    child_names = fields.Text(
        string='Linked Contracts', compute='_compute_child_names',
    )

    @api.depends('contract_id')
    def _compute_child_names(self):
        for rec in self:
            running = rec.contract_id.child_contract_ids.filtered(
                lambda c: c.state == 'active'
            )
            rec.child_names = '\n'.join(running.mapped('display_name'))

    def action_confirm(self):
        self.ensure_one()
        self.contract_id._do_terminate()
        return {'type': 'ir.actions.act_window_close'}
