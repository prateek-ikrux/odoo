# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# The recipient lists the Select everyone and Clear buttons may fill, each a
# field of the company. The button names the list in its context.
RECIPIENT_FIELDS = ('contracts_reminder_recipient_ids', 'contracts_change_recipient_ids')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Not a system parameter: this is the scheduled action's own active flag,
    # so switching it off stops the nightly run outright rather than leaving it
    # to wake up and find nothing to do.
    contracts_reminders_enabled = fields.Boolean(
        string='Expiry Reminders',
        help="Email a reminder before a contract runs out. Turning this off "
             "deactivates the nightly scheduled action.",
    )

    # Shown as chips, but still saved to the 'contracts.reminder_days' system
    # parameter the reminder cron reads; get_values and set_values translate.
    contracts_reminder_milestone_ids = fields.Many2many(
        'contracts.reminder.milestone', string='Send at',
        help="When reminders go out, in days before the end date. The most "
             "urgent one reached is the one sent.",
    )
    # Users rather than free-text addresses, so a recipient who leaves is
    # simply archived; held on the company because a settings field cannot
    # keep a many2many in a system parameter.
    contracts_reminder_recipient_ids = fields.Many2many(
        related='company_id.contracts_reminder_recipient_ids', readonly=False,
    )

    # ── Change notifications ──────────────────────────────────────
    contracts_change_notify = fields.Boolean(
        string='Change Notifications',
        config_parameter='contracts.change_notify',
        help="Email the recipients below as soon as a contract is created, "
             "deleted or has a change recorded in its audit log.",
    )
    contracts_change_recipient_ids = fields.Many2many(
        related='company_id.contracts_change_recipient_ids', readonly=False,
    )

    # ── Reminder scheduled action ─────────────────────────────────
    def _get_reminder_cron(self):
        """The reminder cron, found whether it is currently on or off."""
        return self.sudo().with_context(active_test=False).env.ref(
            'contracts.ir_cron_contract_expiry_reminders',
            raise_if_not_found=False,
        )

    @api.model
    def get_values(self):
        values = super().get_values()
        cron = self._get_reminder_cron()
        values['contracts_reminders_enabled'] = bool(cron and cron.active)
        # Any number in the parameter not yet offered as a chip - set from
        # developer mode, say - becomes one, so saving cannot drop it.
        Milestone = self.env['contracts.reminder.milestone'].sudo()
        milestones = Milestone.browse()
        for days in self.env['contracts.contract']._get_reminder_days():
            milestones |= Milestone._get_or_create(days)
        values['contracts_reminder_milestone_ids'] = [(6, 0, milestones.ids)]
        return values

    def set_values(self):
        super().set_values()
        days = sorted(set(self.contracts_reminder_milestone_ids.mapped('days')), reverse=True)
        self.env['ir.config_parameter'].sudo().set_param(
            'contracts.reminder_days', ','.join(map(str, days)))
        cron = self._get_reminder_cron()
        if cron and cron.active != self.contracts_reminders_enabled:
            cron.active = self.contracts_reminders_enabled

    # ── Select everyone / Clear ───────────────────────────────────
    def action_contracts_recipients_select_all(self):
        """Put every internal user who can be emailed on the list."""
        self._contracts_set_recipients(self.env['res.users'].search([
            ('share', '=', False), ('email', '!=', False)]))

    def action_contracts_recipients_clear(self):
        """Take everyone off the list."""
        self._contracts_set_recipients(self.env['res.users'])

    def _contracts_set_recipients(self, users):
        fname = self.env.context.get('recipient_field')
        if fname not in RECIPIENT_FIELDS:
            raise UserError(_('Unknown recipient list: %s', fname))
        # Straight onto the company: the settings form saves before running
        # a button and reloads after, so the list shows the change at once.
        self.company_id[fname] = users
