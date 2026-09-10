# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

STATE_SELECTION = [
    ('active', 'Active'),
    ('expired', 'Expired'),
    ('terminated', 'Terminated'),
]

STATE_LABELS = dict(STATE_SELECTION)

# Internal discriminator. The two window actions set it through
# ``default_contract_type`` and filter on it, so it is never rendered.
TYPE_SELECTION = [
    ('msa', 'Master Service Agreement'),
    ('sow', 'Statement of Work'),
]


class Contract(models.Model):
    _name = 'contracts.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contract'
    _order = 'end_date desc, id desc'

    # ── Core fields ───────────────────────────────────────────────
    contract_type = fields.Selection(
        TYPE_SELECTION, required=True, index=True, copy=True,
    )
    parent_contract_id = fields.Many2one(
        'contracts.contract', string='Parent Contract',
        domain="[('contract_type', '=', 'msa')]",
        ondelete='restrict', index=True, tracking=True,
        help="The overarching contract this one is placed under.",
    )
    child_contract_ids = fields.One2many(
        'contracts.contract', 'parent_contract_id', string='Linked Contracts',
    )
    active_child_count = fields.Integer(
        compute='_compute_active_child_count',
    )
    client = fields.Char(
        string='Client', required=True, tracking=True, index=True,
        compute='_compute_client', store=True, readonly=False, precompute=True,
        recursive=True,
    )
    candidate = fields.Char(
        string='Candidate', tracking=True,
        help="Person placed with the client under this contract.",
    )
    role = fields.Char(
        string='Role', tracking=True,
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
    @api.depends('contract_type', 'client', 'role', 'candidate')
    def _compute_display_name(self):
        for rec in self:
            if rec.contract_type == 'sow':
                parts = [rec.client, rec.role or rec.candidate]
            else:
                parts = [rec.client]
            rec.display_name = ' - '.join(p for p in parts if p) or _('New Contract')

    # ── Computes ──────────────────────────────────────────────────
    @api.depends('contract_type', 'parent_contract_id.client')
    def _compute_client(self):
        """A placed contract always shows the client of the contract above it."""
        for rec in self:
            if rec.contract_type == 'sow' and rec.parent_contract_id:
                rec.client = rec.parent_contract_id.client
            elif not rec.client:
                rec.client = False

    @api.depends('child_contract_ids.state')
    def _compute_active_child_count(self):
        for rec in self:
            rec.active_child_count = len(
                rec.child_contract_ids.filtered(lambda c: c.state == 'active')
            )

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

    @api.constrains('contract_type', 'parent_contract_id')
    def _check_parent_contract(self):
        for rec in self:
            if rec.contract_type == 'sow':
                if not rec.parent_contract_id:
                    raise ValidationError(
                        _("A parent contract is required on contract '%s'.",
                          rec.display_name)
                    )
                if rec.parent_contract_id.contract_type != 'msa':
                    raise ValidationError(
                        _("Contract '%s' cannot be used as a parent contract.",
                          rec.parent_contract_id.display_name)
                    )
            elif rec.parent_contract_id:
                raise ValidationError(
                    _("Contract '%s' cannot be placed under another contract.",
                      rec.display_name)
                )
            if rec.parent_contract_id == rec:
                raise ValidationError(
                    _("Contract '%s' cannot be its own parent.", rec.display_name)
                )

    @api.constrains('contract_type', 'role', 'candidate')
    def _check_sow_fields(self):
        for rec in self:
            if rec.contract_type != 'sow':
                continue
            if not rec.role:
                raise ValidationError(
                    _("A role is required on contract '%s'.", rec.display_name)
                )
            if not rec.candidate:
                raise ValidationError(
                    _("A candidate is required on contract '%s'.", rec.display_name)
                )

    @api.constrains('contract_type', 'parent_contract_id', 'start_date', 'end_date')
    def _check_parent_period(self):
        for rec in self:
            parent = rec.parent_contract_id
            if rec.contract_type != 'sow' or not parent:
                continue
            if not (parent.start_date and parent.end_date):
                continue
            if rec.start_date < parent.start_date or rec.end_date > parent.end_date:
                raise ValidationError(
                    _("Contract '%(name)s' must run inside the period of the parent "
                      "contract (%(start)s to %(end)s).",
                      name=rec.display_name,
                      start=parent.start_date, end=parent.end_date)
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
        for vals in vals_list:
            # Checked up front: without a parent the client cannot be derived,
            # so the insert would fail on the NOT NULL column instead of here.
            if vals.get('contract_type') == 'sow' and not vals.get('parent_contract_id'):
                raise ValidationError(_("A parent contract is required."))
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
        if 'start_date' in vals or 'end_date' in vals:
            # Narrowing a parent's period must not silently leave the contracts
            # placed under it running outside of it.
            self.child_contract_ids._check_parent_period()
        return res

    # ── Actions ───────────────────────────────────────────────────
    def action_terminate(self):
        """Close a contract midway.

        Closing a contract that still has running contracts placed under it
        goes through a confirmation first, so the ones affected are named
        before anything changes. Nothing cascades either way.
        """
        self.ensure_one()
        if self.active_child_count:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'contracts.terminate.confirm',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_contract_id': self.id},
            }
        return self._do_terminate()

    def _do_terminate(self):
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
