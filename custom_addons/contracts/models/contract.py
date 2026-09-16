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

# Fallback for the 'contracts.reminder_days' system parameter: how many days
# before the end date an expiry reminder goes out.
DEFAULT_REMINDER_DAYS = '45,30,7'


class Contract(models.Model):
    _name = 'contracts.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contract'
    _order = 'effective_end_date desc, id desc'

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
    reminder_sent_days = fields.Integer(
        string='Last Reminder', readonly=True, copy=False,
        help="Day milestone of the most recent expiry reminder sent for this "
             "contract. Zero means none has been sent yet. Reset whenever the "
             "end date changes, so a renewal starts the sequence over.",
    )
    reminder_last_sent = fields.Date(
        string='Reminder Sent On', readonly=True, copy=False,
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
    annual_appraisal_due = fields.Date(
        string='Annual Appraisal Due',
        compute='_compute_annual_appraisal_due', store=True,
        help="Next anniversary of the start date still to come.",
    )
    remarks = fields.Text(string='Remarks')

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

    @api.depends('child_contract_ids')
    def _compute_child_contract_count(self):
        for rec in self:
            rec.child_contract_count = len(rec.child_contract_ids)

    @api.depends('end_date', 'extended_end_date')
    def _compute_effective_end_date(self):
        """An extension, once recorded, is what the contract actually runs to."""
        for rec in self:
            rec.effective_end_date = rec.extended_end_date or rec.end_date

    @api.depends('start_date')
    def _compute_annual_appraisal_due(self):
        """The next start-date anniversary that has not passed yet.

        Stored, so it can be sorted and filtered on, which means it goes stale
        as anniversaries pass - the nightly cron refreshes the ones that have.
        """
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.start_date:
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
            if not (parent.start_date and parent.effective_end_date):
                continue
            # Compared on the effective dates: extending a placed contract past
            # the contract above it means that one has to be extended first.
            if rec.start_date < parent.start_date \
                    or rec.effective_end_date > parent.effective_end_date:
                raise ValidationError(
                    _("Contract '%(name)s' must run inside the period of the parent "
                      "contract (%(start)s to %(end)s).",
                      name=rec.display_name,
                      start=parent.start_date, end=parent.effective_end_date)
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
            lambda c: c.state == 'active' and c.effective_end_date
            and c.effective_end_date < today
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
        if 'end_date' in vals or 'extended_end_date' in vals:
            # A renewal or an extension pushes the end out, which has to re-arm
            # the whole reminder sequence. setdefault keeps the cron's own write
            # - which sets the marker and touches neither date - out of the way.
            vals.setdefault('reminder_sent_days', 0)
            vals.setdefault('reminder_last_sent', False)
        res = super().write(vals)
        if 'attachment_ids' in vals:
            self._link_attachments_to_record()
        if 'end_date' in vals or 'extended_end_date' in vals or 'state' in vals:
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
