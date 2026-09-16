# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.mail import email_normalize, single_email_re

from .contract import DEFAULT_REMINDER_DAYS


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

    # These two are stored as system parameters, which is what
    # contracts.contract reads. This screen only makes them editable without
    # developer mode, and refuses values the reminder cron would silently drop.
    contracts_reminder_days = fields.Char(
        string='Reminder Schedule',
        config_parameter='contracts.reminder_days',
        default=DEFAULT_REMINDER_DAYS,
        help="Days before the end date an expiry reminder goes out, comma "
             "separated. The most urgent milestone reached is the one sent.",
    )
    # Deliberately no default: get_param falls back to the default when the
    # stored value is an empty string, so one here would quietly reinstate
    # recipients on a database where they were cleared on purpose.
    contracts_reminder_emails = fields.Char(
        string='Reminder Recipients',
        config_parameter='contracts.reminder_emails',
        help="Comma-separated addresses that receive expiry reminders. "
             "Leave empty to send none.",
    )

    @api.constrains('contracts_reminder_days', 'contracts_reminder_emails')
    def _check_contracts_reminder_settings(self):
        """Refuse what the cron would otherwise drop without telling anyone."""
        for rec in self:
            for chunk in (rec.contracts_reminder_days or '').split(','):
                chunk = chunk.strip()
                if not chunk:
                    continue
                if not chunk.isdigit() or int(chunk) <= 0:
                    raise ValidationError(
                        _("'%s' is not a valid number of days. Enter whole "
                          "numbers above zero, separated by commas - for "
                          "example 45,30,7.", chunk)
                    )
            for token in (rec.contracts_reminder_emails or '').split(','):
                token = token.strip()
                if not token:
                    continue
                # email_normalize only extracts an address - it returns
                # '@nope' and 'x@y' happily - so the extracted value still has
                # to be checked against the strict pattern. Going through it
                # first is what lets 'Bob <b@c.com>' through.
                normalized = email_normalize(token)
                if not normalized or not single_email_re.match(normalized):
                    raise ValidationError(
                        _("'%s' is not a valid email address. Separate "
                          "recipients with commas.", token)
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
        return values

    def set_values(self):
        super().set_values()
        cron = self._get_reminder_cron()
        if cron and cron.active != self.contracts_reminders_enabled:
            cron.active = self.contracts_reminders_enabled
