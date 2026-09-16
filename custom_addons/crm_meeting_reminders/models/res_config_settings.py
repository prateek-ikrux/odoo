# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.mail import email_normalize, single_email_re

from .calendar_event import (
    DEFAULT_REMINDER_HOURS, PARAM_CC, PARAM_FROM, PARAM_HOURS,
)

CRON_XMLID = 'crm_meeting_reminders.ir_cron_crm_meeting_reminders'


def _valid_email(token):
    """email_normalize only extracts an address - it returns '@nope' and 'x@y'
    happily - so the extracted value still has to be checked against the strict
    pattern. Going through it first is what lets 'Bob <b@c.com>' through."""
    normalized = email_normalize(token)
    return bool(normalized and single_email_re.match(normalized))


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Not a system parameter: this is the scheduled action's own active flag,
    # so switching it off stops the run outright.
    crm_meeting_reminders_enabled = fields.Boolean(
        string='Meeting Reminders',
        help="Email a reminder before a meeting linked to an opportunity. "
             "Turning this off deactivates the scheduled action.",
    )
    crm_meeting_reminder_hours = fields.Char(
        string='Meeting Reminder Schedule',
        config_parameter=PARAM_HOURS,
        default=DEFAULT_REMINDER_HOURS,
        help="Hours before the meeting starts that a reminder goes out, comma "
             "separated. The most urgent milestone reached is the one sent.",
    )
    # Deliberately no default: get_param falls back to the default when the
    # stored value is an empty string, so one here would quietly reinstate
    # recipients on a database where they were cleared on purpose.
    crm_meeting_reminder_cc = fields.Char(
        string='Always Copy',
        config_parameter=PARAM_CC,
        help="Addresses copied on every meeting reminder, whether or not they "
             "are attending. Leave empty to copy nobody.",
    )
    crm_meeting_reminder_from = fields.Char(
        string='Send From',
        config_parameter=PARAM_FROM,
        help="Address these reminders are sent from. Set it to a mailbox the "
             "outgoing mail server is allowed to send as. Replies still go to "
             "the meeting organiser. Leave empty to use the Odoo default.",
    )

    @api.constrains('crm_meeting_reminder_hours', 'crm_meeting_reminder_cc',
                    'crm_meeting_reminder_from')
    def _check_crm_meeting_reminder_settings(self):
        """Refuse what the cron would otherwise drop without telling anyone."""
        for rec in self:
            for chunk in (rec.crm_meeting_reminder_hours or '').split(','):
                chunk = chunk.strip()
                if not chunk:
                    continue
                if not chunk.isdigit() or int(chunk) <= 0:
                    raise ValidationError(
                        _("'%s' is not a valid number of hours. Enter whole "
                          "numbers above zero, separated by commas - for "
                          "example 48,24,12,1.", chunk)
                    )
            for token in (rec.crm_meeting_reminder_cc or '').split(','):
                token = token.strip()
                if token and not _valid_email(token):
                    raise ValidationError(
                        _("'%s' is not a valid email address. Separate "
                          "addresses with commas.", token)
                    )
            sender = (rec.crm_meeting_reminder_from or '').strip()
            if sender and not _valid_email(sender):
                raise ValidationError(
                    _("'%s' is not a valid sending address.", sender)
                )

    # ── Scheduled action ──────────────────────────────────────────
    def _get_meeting_reminder_cron(self):
        """The reminder cron, found whether it is currently on or off."""
        return self.sudo().with_context(active_test=False).env.ref(
            CRON_XMLID, raise_if_not_found=False)

    @api.model
    def get_values(self):
        values = super().get_values()
        cron = self._get_meeting_reminder_cron()
        values['crm_meeting_reminders_enabled'] = bool(cron and cron.active)
        return values

    def set_values(self):
        super().set_values()
        cron = self._get_meeting_reminder_cron()
        if cron and cron.active != self.crm_meeting_reminders_enabled:
            cron.active = self.crm_meeting_reminders_enabled
