# -*- coding: utf-8 -*-
import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

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

YES_NO_SELECTION = [
    ('no', 'No'),
    ('yes', 'Yes'),
]

BILLING_CURRENCY_SELECTION = [
    ('inr', 'INR'),
    ('usd', 'USD'),
    ('other', 'Others'),
]

BILLING_FREQUENCY_SELECTION = [
    ('monthly', 'Monthly'),
    ('quarterly', 'Quarterly'),
    ('yearly', 'Yearly'),
]

# An overarching contract either runs to a date or runs for as long as there is
# work under it. The second kind has no end date at all, rather than a made-up
# one, so it never expires, never counts down and never sends a reminder.
TERM_SELECTION = [
    ('fixed', 'Fixed End Date'),
    ('until_completion', 'Until Completion of Service'),
]

# Set on the overarching contract and copied down to the ones placed under it.
BILLING_FIELDS = [
    'bill_rate',
    'billing_currency',
    'billing_currency_other',
    'billing_frequency',
    'billing_poc',
    'billing_start_date',
]

# Fallback for the 'contracts.reminder_days' system parameter: how many days
# before the end date an expiry reminder goes out.
DEFAULT_REMINDER_DAYS = '45,30,7'


class Contract(models.Model):
    _name = 'contracts.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contract'
    _order = 'effective_end_date desc, id desc'
    # There is no name field, and without this a search on the display name -
    # typing in a many2one, or an import matching by name - matches every
    # contract instead of filtering.
    _rec_names_search = ['client', 'candidate', 'role']

    # ── Core fields ───────────────────────────────────────────────
    contract_type = fields.Selection(
        TYPE_SELECTION, required=True, index=True, copy=True,
    )
    parent_contract_id = fields.Many2one(
        'contracts.contract', string='Parent Contract',
        # A terminated contract is not offered for new placements. Not a
        # constraint: placements made before it was terminated stay valid, and
        # an import of past placements still has to be able to name it.
        domain="[('contract_type', '=', 'msa'), ('state', '!=', 'terminated')]",
        ondelete='restrict', index=True, tracking=True,
        help="The overarching contract this one is placed under.",
    )
    child_contract_ids = fields.One2many(
        'contracts.contract', 'parent_contract_id', string='Linked Contracts',
    )
    active_child_count = fields.Integer(
        compute='_compute_active_child_count',
    )
    child_contract_count = fields.Integer(
        string='# Linked Contracts', compute='_compute_child_contract_count',
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
        string='TA POC', required=True, tracking=True,
        help="Talent acquisition point of contact for this contract.",
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
    term = fields.Selection(
        TERM_SELECTION, string='Contract Term',
        required=True, default='fixed', tracking=True,
        help="Until Completion of Service: the contract runs for as long as "
             "there is work under it and has no end date. Only an overarching "
             "contract can run this way.",
    )
    # Required unless the contract runs until completion of service; held by
    # _check_end_date rather than on the column, which has to allow the gap.
    end_date = fields.Date(
        string='End Date', tracking=True,
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
    reminder_sent_days = fields.Integer(
        string='Last Reminder', readonly=True, copy=False,
        help="Day milestone of the most recent expiry reminder sent for this "
             "contract. Zero means none has been sent yet. Reset whenever the "
             "end date changes, so a renewal starts the sequence over.",
    )
    reminder_last_sent = fields.Date(
        string='Reminder Sent On', readonly=True, copy=False,
    )
    is_extended = fields.Selection(
        YES_NO_SELECTION, string='Is Contract Getting Extended?',
        required=True, default='no', tracking=True, copy=False,
        help="Answer Yes to record an Extended End Date. Answering No clears it.",
    )
    extended_end_date = fields.Date(
        string='Extended End Date', tracking=True, copy=False,
        help="Set when the contract is extended beyond its original end date. "
             "Once set it - not the end date - decides when the contract "
             "expires and when expiry reminders go out.",
    )
    effective_end_date = fields.Date(
        string='Effective End Date',
        compute='_compute_effective_end_date', store=True, index=True,
        help="The date the contract actually runs to: the extended end date "
             "when one is set, otherwise the end date.",
    )
    is_appraisal_due = fields.Selection(
        YES_NO_SELECTION, string='Is Annual Appraisal Due?',
        required=True, default='no', tracking=True,
        help="Answer Yes to track the next annual appraisal date. "
             "Answering No clears it.",
    )
    annual_appraisal_due = fields.Date(
        string='Annual Appraisal Due',
        compute='_compute_annual_appraisal_due', store=True,
        help="Next anniversary of the start date still to come.",
    )
    remarks = fields.Text(string='Remarks')

    # ── Billing ───────────────────────────────────────────────────
    # Agreed on the overarching contract. A placed contract bills on the same
    # terms, so it takes every one of them from the contract above it.
    bill_rate = fields.Float(
        string='Bill Rate', digits=(5, 2), tracking=True,
        compute='_compute_billing', store=True, readonly=False, precompute=True,
        recursive=True,
        help="Bill rate, as a percentage.",
    )
    billing_currency = fields.Selection(
        BILLING_CURRENCY_SELECTION, string='Billing Currency', tracking=True,
        compute='_compute_billing', store=True, readonly=False, precompute=True,
        recursive=True,
    )
    billing_currency_other = fields.Char(
        string='Other Currency', tracking=True,
        compute='_compute_billing', store=True, readonly=False, precompute=True,
        recursive=True,
        help="The currency billed in, when it is neither INR nor USD.",
    )
    billing_frequency = fields.Selection(
        BILLING_FREQUENCY_SELECTION, string='Billing Frequency', tracking=True,
        compute='_compute_billing', store=True, readonly=False, precompute=True,
        recursive=True,
    )
    billing_poc = fields.Char(
        string='Billing POC', tracking=True,
        compute='_compute_billing', store=True, readonly=False, precompute=True,
        recursive=True,
        help="Person in charge of billing for this contract. Never the same "
             "person as the TA POC.",
    )
    billing_start_date = fields.Date(
        string='Billing Start Date', tracking=True,
        compute='_compute_billing', store=True, readonly=False, precompute=True,
        recursive=True,
    )

    # ── Display name ──────────────────────────────────────────────
    @api.depends('contract_type', 'client', 'role', 'candidate',
                 'start_date', 'effective_end_date', 'term')
    @api.depends_context('contracts_show_period')
    def _compute_display_name(self):
        """Client, plus the placement for a placed contract.

        Where an overarching contract is being picked, the context asks for its
        period as well: one client can hold several of them over the years,
        and by name alone they are indistinguishable.
        """
        show_period = self.env.context.get('contracts_show_period')
        for rec in self:
            if rec.contract_type == 'sow':
                parts = [rec.client, rec.role or rec.candidate]
            else:
                parts = [rec.client]
            name = ' - '.join(p for p in parts if p) or _('New Contract')
            if show_period and rec.contract_type == 'msa' and rec.start_date:
                name = _('%(name)s (%(start)s to %(end)s)',
                         name=name,
                         start=rec.start_date.strftime('%d/%m/%y'),
                         end=rec.effective_end_date.strftime('%d/%m/%y')
                         if rec.effective_end_date else _('Completion of Service'))
            rec.display_name = name

    # ── Computes ──────────────────────────────────────────────────
    @api.depends('contract_type', 'parent_contract_id.client')
    def _compute_client(self):
        """A placed contract always shows the client of the contract above it."""
        for rec in self:
            if rec.contract_type == 'sow' and rec.parent_contract_id:
                rec.client = rec.parent_contract_id.client
            elif not rec.client:
                rec.client = False

    @api.depends('contract_type', *(f'parent_contract_id.{f}' for f in BILLING_FIELDS))
    def _compute_billing(self):
        """A placed contract always bills on the terms of the contract above it."""
        for rec in self:
            if rec.contract_type == 'sow' and rec.parent_contract_id:
                for fname in BILLING_FIELDS:
                    rec[fname] = rec.parent_contract_id[fname]
            else:
                for fname in BILLING_FIELDS:
                    if not rec[fname]:
                        rec[fname] = False

    @api.depends('child_contract_ids.state')
    def _compute_active_child_count(self):
        for rec in self:
            rec.active_child_count = len(
                rec.child_contract_ids.filtered(lambda c: c.state == 'active')
            )

    @api.depends('child_contract_ids')
    def _compute_child_contract_count(self):
        for rec in self:
            rec.child_contract_count = len(rec.child_contract_ids)

    @api.depends('end_date', 'extended_end_date')
    def _compute_effective_end_date(self):
        """An extension, once recorded, is what the contract actually runs to."""
        for rec in self:
            rec.effective_end_date = rec.extended_end_date or rec.end_date

    @api.depends('start_date', 'is_appraisal_due')
    def _compute_annual_appraisal_due(self):
        """The next start-date anniversary that has not passed yet, or nothing
        when no appraisal is due on this contract.

        Stored, so it can be sorted and filtered on, which means it goes stale
        as anniversaries pass - the nightly cron refreshes the ones that have.
        """
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.is_appraisal_due != 'yes' or not rec.start_date:
                rec.annual_appraisal_due = False
                continue
            due = rec.start_date
            while due <= today:
                due += relativedelta(years=1)
            rec.annual_appraisal_due = due

    @api.depends('effective_end_date', 'state')
    def _compute_days_left(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state in ('expired', 'terminated') or not rec.effective_end_date:
                rec.days_left = 0
            else:
                rec.days_left = (rec.effective_end_date - today).days

    def _search_days_left(self, operator, value):
        """Translate a search on days_left into one on the effective end date.

        Only meaningful for contracts that still run, so the domain is
        restricted to the active ones.
        """
        if not isinstance(value, int):
            raise ValidationError(_("'Days Left' can only be compared to a whole number."))
        today = fields.Date.context_today(self)
        # days_left = effective_end_date - today
        #   =>  effective_end_date = today + days_left.
        # The operator carries over unchanged because the mapping is increasing.
        target = fields.Date.add(today, days=value)
        return [('state', '=', 'active'), ('effective_end_date', operator, target)]

    @api.onchange('is_extended')
    def _onchange_is_extended(self):
        """Clear the hidden date straight away, so the form stops showing an
        effective end date taken from it."""
        if self.is_extended != 'yes':
            self.extended_end_date = False

    @api.onchange('billing_currency')
    def _onchange_billing_currency(self):
        """The free-text currency only means something under Others."""
        if self.billing_currency != 'other':
            self.billing_currency_other = False

    @api.model
    def _normalize_extension_vals(self, vals, records=None):
        """Keep the extension answer and the extended date in step.

        Answering No wipes the date; a date written without an answer (an
        import, a script) is taken as a Yes. ``records`` is the recordset
        being written, so a No that changes nothing does not add the date to
        the values and needlessly re-arm the reminder sequence.
        """
        if vals.get('term') == 'until_completion':
            # No end date, so nothing to extend: whatever came with it goes.
            vals.update(end_date=False, is_extended='no')
        if vals.get('is_extended') == 'no':
            if records is None or any(records.mapped('extended_end_date')):
                vals['extended_end_date'] = False
        elif vals.get('extended_end_date') and 'is_extended' not in vals:
            vals['is_extended'] = 'yes'
        return vals

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

        Only files that belong to no record yet are taken. A file already on
        another record - an import naming one that sits on a different contract
        or a CRM lead - stays where it is and is only linked from here, rather
        than being pulled off the record it came from.
        """
        for rec in self:
            stray = rec.attachment_ids.filtered(lambda a: not a.res_id)
            if stray:
                stray.write({'res_model': rec._name, 'res_id': rec.id})

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec._get_documents())

    # ── Constraints ───────────────────────────────────────────────
    @api.constrains('contract_type', 'term', 'end_date', 'extended_end_date')
    def _check_end_date(self):
        for rec in self:
            if rec.term == 'until_completion':
                if rec.contract_type != 'msa':
                    raise ValidationError(
                        _("Only a Master Service Agreement can run until completion "
                          "of service; contract '%s' needs an end date.",
                          rec.display_name)
                    )
                # Writing the term clears both dates, so one can only be here if
                # it was written on its own afterwards. The form hides them for
                # this term, so a date let through would count down, remind and
                # expire the contract with nobody able to see why.
                if rec.end_date or rec.extended_end_date:
                    raise ValidationError(
                        _("Contract '%s' runs until completion of service and cannot "
                          "have an end date. Change its Contract Term to Fixed End "
                          "Date first.", rec.display_name)
                    )
            elif not rec.end_date:
                raise ValidationError(
                    _("An End Date is required on contract '%s', unless it runs "
                      "until completion of service.", rec.display_name)
                )

    @api.constrains('start_date', 'end_date', 'extended_end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(
                    _("End Date cannot be earlier than Start Date on contract '%s'.",
                      rec.display_name)
                )
            # An extension that moves the end date backwards is a correction,
            # not an extension, and would quietly shorten the contract.
            if rec.extended_end_date and rec.end_date \
                    and rec.extended_end_date < rec.end_date:
                raise ValidationError(
                    _("Extended End Date cannot be earlier than End Date on "
                      "contract '%s'.", rec.display_name)
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

    @api.constrains('contract_type', 'parent_contract_id', 'start_date',
                    'end_date', 'extended_end_date')
    def _check_parent_period(self):
        for rec in self:
            parent = rec.parent_contract_id
            if rec.contract_type != 'sow' or not parent:
                continue
            if not parent.start_date:
                continue
            # Compared on the effective dates: extending a placed contract past
            # the contract above it means that one has to be extended first.
            # A parent running until completion of service has no end to
            # outrun, but a placement still cannot start before it.
            if rec.start_date < parent.start_date \
                    or (parent.effective_end_date and rec.effective_end_date
                        and rec.effective_end_date > parent.effective_end_date):
                raise ValidationError(
                    _("Contract '%(name)s' must run inside the period of the parent "
                      "contract (%(start)s to %(end)s).",
                      name=rec.display_name,
                      start=parent.start_date,
                      end=parent.effective_end_date or _("completion of service"))
                )

    @api.constrains('poc', 'billing_poc')
    def _check_billing_poc(self):
        for rec in self:
            if not (rec.poc and rec.billing_poc) \
                    or rec.poc.strip().casefold() != rec.billing_poc.strip().casefold():
                continue
            if rec.contract_type == 'sow':
                raise ValidationError(
                    _("The TA POC on contract '%(name)s' cannot be %(poc)s, who is "
                      "the Billing POC on its parent contract '%(parent)s'.",
                      name=rec.display_name, poc=rec.billing_poc,
                      parent=rec.parent_contract_id.display_name)
                )
            raise ValidationError(
                _("The Billing POC cannot be the same person as the TA POC "
                  "on contract '%s'.", rec.display_name)
            )

    @api.constrains('bill_rate', 'billing_currency', 'billing_currency_other')
    def _check_billing(self):
        for rec in self:
            if rec.bill_rate < 0:
                raise ValidationError(
                    _("Bill Rate cannot be negative on contract '%s'.", rec.display_name)
                )
            if rec.billing_currency == 'other' and not (rec.billing_currency_other or '').strip():
                raise ValidationError(
                    _("Name the billing currency on contract '%s'.", rec.display_name)
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
        """Keep 'expired' in step with the date the contract runs to.

        Both ways: an active contract whose effective end date has passed
        becomes expired, and an expired one whose dates now run on - extended
        after it lapsed, or switched to run until completion of service -
        comes back to active. Terminated is a decision, not a date, so it is
        never touched here.

        Uses ``super().write`` so it cannot recurse through :meth:`write`
        while still going through mail.thread and keeping the tracking log.
        """
        today = fields.Date.context_today(self)

        def ended(contract):
            return contract.effective_end_date and contract.effective_end_date < today

        to_expire = self.filtered(lambda c: c.state == 'active' and ended(c))
        to_revive = self.filtered(lambda c: c.state == 'expired' and not ended(c))
        if to_expire:
            super(Contract, to_expire).write({'state': 'expired'})
        if to_revive:
            super(Contract, to_revive).write({'state': 'active'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Checked up front: without a parent the client cannot be derived,
            # so the insert would fail on the NOT NULL column instead of here.
            if vals.get('contract_type') == 'sow' and not vals.get('parent_contract_id'):
                raise ValidationError(_("A parent contract is required."))
            if vals.get('contract_type') == 'sow':
                # Taken from the parent; anything passed in would override that.
                for fname in BILLING_FIELDS:
                    vals.pop(fname, None)
            self._normalize_extension_vals(vals)
        records = super().create(vals_list)
        records._link_attachments_to_record()
        # @api.constrains only fires for fields present in the values, so a
        # create that never mentions attachment_ids would slip through.
        records._check_attachments()
        records._sync_expired_state()
        return records

    def write(self, vals):
        self._normalize_extension_vals(vals, self)
        if 'end_date' in vals or 'extended_end_date' in vals:
            # A renewal or an extension pushes the end out, which has to re-arm
            # the whole reminder sequence. setdefault keeps the cron's own write
            # - which sets the marker and touches neither date - out of the way.
            vals.setdefault('reminder_sent_days', 0)
            vals.setdefault('reminder_last_sent', False)
        res = super().write(vals)
        if any(fname in vals for fname in BILLING_FIELDS) \
                and not self.env.context.get('contracts_billing_sync'):
            # A placed contract cannot be given billing terms of its own; put
            # back the ones of the contract above it. Called outside of a
            # recompute, the assignments come back through here - hence the flag.
            self.filtered(lambda c: c.contract_type == 'sow') \
                .with_context(contracts_billing_sync=True)._compute_billing()
        if 'attachment_ids' in vals:
            self._link_attachments_to_record()
        if any(fname in vals for fname in ('end_date', 'extended_end_date', 'term', 'state')):
            self._sync_expired_state()
        if 'start_date' in vals or 'end_date' in vals \
                or 'extended_end_date' in vals:
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
            rec.write({
                'state': 'active',
                'termination_date': False,
                # Back in the running, so the reminder sequence starts over.
                'reminder_sent_days': 0,
                'reminder_last_sent': False,
            })
        return True

    def action_view_child_contracts(self):
        """Open the contracts placed under this one, in the SOW screen."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'contracts.action_contracts_sow'
        )
        action['domain'] = [('parent_contract_id', '=', self.id)]
        action['context'] = {
            'default_contract_type': 'sow',
            'default_parent_contract_id': self.id,
        }
        return action

    def action_open_parent_contract(self):
        """Open the contract this one is placed under."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.parent_contract_id.id,
            'view_mode': 'form',
            'views': [(self.env.ref('contracts.view_contracts_contract_form').id, 'form')],
        }

    def action_open_report_wizard(self):
        """Open the Excel export wizard."""
        return self.env['ir.actions.act_window']._for_xml_id(
            'contracts.action_contracts_report_wizard'
        )

    # ── Reminder configuration ────────────────────────────────────
    @api.model
    def _get_reminder_days(self):
        """Day milestones an expiry reminder goes out on, most distant first.

        Read from the 'contracts.reminder_days' system parameter so the
        schedule can be changed without a deploy. Anything that is not a
        plain number is ignored rather than breaking the run.
        """
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'contracts.reminder_days', DEFAULT_REMINDER_DAYS)
        days = set()
        for chunk in (raw or '').split(','):
            chunk = chunk.strip()
            if chunk.isdigit() and int(chunk) > 0:
                days.add(int(chunk))
        return sorted(days, reverse=True)

    @api.model
    def _get_reminder_recipients(self):
        """Who expiry reminders go to, as a comma-separated address list.

        The contract itself carries no email address - the client and the POC
        are free text - so the recipients are an internal list held in the
        'contracts.reminder_emails' system parameter.
        """
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'contracts.reminder_emails', '')
        return ','.join(e.strip() for e in (raw or '').split(',') if e.strip())

    # ── Scheduled actions ─────────────────────────────────────────
    @api.model
    def _cron_expire_contracts(self):
        """Move contracts past their end date to 'Expired'. Runs nightly.

        Also rolls the appraisal date forward: it is a stored compute that
        only depends on the start date, so an anniversary passing does not
        invalidate it on its own.
        """
        today = fields.Date.context_today(self)
        contracts = self.search([
            ('state', '=', 'active'),
            ('effective_end_date', '<', today),
        ])
        if contracts:
            contracts.write({'state': 'expired'})

        stale = self.search([
            ('state', '=', 'active'),
            ('annual_appraisal_due', '<=', today),
        ])
        if stale:
            stale._compute_annual_appraisal_due()
            stale.flush_recordset(['annual_appraisal_due'])
        return True

    @api.model
    def _cron_send_expiry_reminders(self):
        """Warn an internal list before a contract runs out. Runs nightly.

        A milestone is reached once the contract has that many days left or
        fewer. The one sent is the most urgent milestone reached, and only if
        it beats what already went out, which makes a repeated run a no-op and
        still catches up after downtime: a contract that slips from 35 to 5
        days left while the server is off gets the 7 day warning, and the 30
        day one it overtook is dropped rather than sent late.
        """
        days = self._get_reminder_days()
        recipients = self._get_reminder_recipients()
        if not days or not recipients:
            _logger.warning(
                "Contract expiry reminders: no milestones in "
                "'contracts.reminder_days' or no recipients in "
                "'contracts.reminder_emails'; skipping run."
            )
            return True

        template = self.env.ref(
            'contracts.mail_template_contract_expiry_reminder',
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning(
                "Contract expiry reminders: mail template is missing; "
                "skipping run."
            )
            return True

        today = fields.Date.context_today(self)
        # The widest milestone bounds the candidate set; the per-record check
        # below picks the milestone that actually applies.
        contracts = self.search([
            ('state', '=', 'active'),
            ('effective_end_date', '>=', today),
            ('effective_end_date', '<=', fields.Date.add(today, days=max(days))),
        ])

        for rec in contracts:
            reached = [d for d in days if rec.days_left <= d]
            if not reached:
                continue
            milestone = min(reached)
            if rec.reminder_sent_days and milestone >= rec.reminder_sent_days:
                # This milestone, or a less urgent one, already went out.
                continue
            try:
                # A savepoint per record: one bad contract must not abort the
                # whole run, and an error would otherwise leave the cursor
                # unusable for the contracts after it.
                with self.env.cr.savepoint():
                    template.with_context(reminder_days=milestone).send_mail(
                        rec.id,
                        email_values={'email_to': recipients},
                        force_send=False,
                    )
                    rec.write({
                        'reminder_sent_days': milestone,
                        'reminder_last_sent': today,
                    })
            except Exception:
                _logger.exception(
                    "Contract expiry reminder failed for contract %s (id %s).",
                    rec.display_name, rec.id,
                )
        return True
