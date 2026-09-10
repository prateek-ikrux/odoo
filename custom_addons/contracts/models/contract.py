# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

STATE_SELECTION = [
    ('active', 'Active'),
    ('expired', 'Expired'),
    ('terminated', 'Terminated'),
]

STATE_LABELS = dict(STATE_SELECTION)


class Contract(models.Model):
    _name = 'contracts.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contract'
    _order = 'end_date desc, id desc'

    # ── Core fields ───────────────────────────────────────────────
    client = fields.Char(
        string='Client', required=True, tracking=True, index=True,
    )
    role = fields.Char(
        string='Role', required=True, tracking=True,
    )
    poc = fields.Char(
        string='POC', required=True, tracking=True,
        help="Point of contact for this contract.",
    )
    created_by_id = fields.Many2one(
        'res.users', string='Created By',
        related='create_uid', store=True, readonly=True,
        help="User who created the contract. Set automatically and cannot be changed.",
    )
    start_date = fields.Date(
        string='Start Date', required=True, tracking=True,
        default=fields.Date.context_today,
    )
    end_date = fields.Date(
        string='End Date', required=True, tracking=True,
    )
    days_left = fields.Integer(
        string='Days Left', compute='_compute_days_left', search='_search_days_left',
        help="Calendar days remaining until the end date. Zero once the contract "
             "is expired or terminated.",
    )
    state = fields.Selection(
        STATE_SELECTION, string='Status', default='active',
        required=True, tracking=True, copy=False, index=True,
    )
    attachment_ids = fields.Many2many(
        'ir.attachment', 'contracts_contract_attachment_rel',
        'contract_id', 'attachment_id',
        string='Attachments', required=True,
        help="Signed contract documents. At least one attachment is mandatory.",
    )
    attachment_count = fields.Integer(
        string='# Attachments', compute='_compute_attachment_count',
    )
    termination_date = fields.Date(
        string='Termination Date', readonly=True, copy=False,
        help="Date the contract was closed midway.",
    )

    # ── Display name ──────────────────────────────────────────────
    @api.depends('client', 'role')
    def _compute_display_name(self):
        for rec in self:
            parts = [p for p in (rec.client, rec.role) if p]
            rec.display_name = ' - '.join(parts) or _('New Contract')

    # ── Computes ──────────────────────────────────────────────────
    @api.depends('end_date', 'state')
    def _compute_days_left(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state in ('expired', 'terminated') or not rec.end_date:
                rec.days_left = 0
            else:
                rec.days_left = (rec.end_date - today).days

    def _search_days_left(self, operator, value):
        """Translate a search on days_left into a search on end_date.

        Only meaningful for contracts that still run, so the domain is
        restricted to the active ones.
        """
        if not isinstance(value, int):
            raise ValidationError(_("'Days Left' can only be compared to a whole number."))
        today = fields.Date.context_today(self)
        # days_left = end_date - today  =>  end_date = today + days_left.
        # The operator carries over unchanged because the mapping is increasing.
        target = fields.Date.add(today, days=value)
        return [('state', '=', 'active'), ('end_date', operator, target)]

    def _get_documents(self):
        """Every file on the record: uploaded through the form widget, or
        added from the chatter after the contract was saved."""
        self.ensure_one()
        linked = self.env['ir.attachment']
        if self.id:
            linked = linked.search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
            ])
        return self.attachment_ids | linked

    def _link_attachments_to_record(self):
        """Re-point uploaded files at the contract.

        The form widget has to store files before the contract exists, so they
        land with ``res_id`` 0, which keeps them out of the standard
        attachments box until they are re-pointed here.
        """
        for rec in self:
            stray = rec.attachment_ids.filtered(
                lambda a: a.res_model != rec._name or a.res_id != rec.id
            )
            if stray:
                stray.write({'res_model': rec._name, 'res_id': rec.id})

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec._get_documents())

    # ── Constraints ───────────────────────────────────────────────
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(
                    _("End Date cannot be earlier than Start Date on contract '%s'.",
                      rec.display_name)
                )

    @api.constrains('attachment_ids')
    def _check_attachments(self):
        for rec in self:
            if not rec._get_documents():
                raise ValidationError(
                    _("At least one attachment is required on contract '%s'.",
                      rec.display_name)
                )

    # ── State synchronisation ─────────────────────────────────────
    def _sync_expired_state(self):
        """Flip active contracts whose end date has passed to 'expired'.

        Uses ``super().write`` so it cannot recurse through :meth:`write`
        while still going through mail.thread and keeping the tracking log.
        """
        today = fields.Date.context_today(self)
        to_expire = self.filtered(
            lambda c: c.state == 'active' and c.end_date and c.end_date < today
        )
        if to_expire:
            super(Contract, to_expire).write({'state': 'expired'})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._link_attachments_to_record()
        # @api.constrains only fires for fields present in the values, so a
        # create that never mentions attachment_ids would slip through.
        records._check_attachments()
        records._sync_expired_state()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'attachment_ids' in vals:
            self._link_attachments_to_record()
        if 'end_date' in vals or 'state' in vals:
            self._sync_expired_state()
        return res

    # ── Actions ───────────────────────────────────────────────────
    def action_terminate(self):
        """Close a contract midway."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state == 'terminated':
                continue
            rec.write({'state': 'terminated', 'termination_date': today})
        return True

    def action_reset_to_active(self):
        """Undo a termination.

        A contract whose end date has already passed lands back on 'expired'
        rather than 'active' - that is handled by :meth:`_sync_expired_state`.
        """
        for rec in self:
            rec.write({'state': 'active', 'termination_date': False})
        return True

    def action_open_report_wizard(self):
        """Open the Excel export wizard."""
        return self.env['ir.actions.act_window']._for_xml_id(
            'contracts.action_contracts_report_wizard'
        )

    # ── Scheduled action ──────────────────────────────────────────
    @api.model
    def _cron_expire_contracts(self):
        """Move contracts past their end date to 'Expired'. Runs nightly."""
        today = fields.Date.context_today(self)
        contracts = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
        ])
        if contracts:
            contracts.write({'state': 'expired'})
        return True
