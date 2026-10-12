# -*- coding: utf-8 -*-
from datetime import timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# When the daily change summary goes out until someone picks otherwise.
DEFAULT_SUMMARY_TIME = 23.5


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
        help="Email the recipients below one summary at the end of each day, "
             "listing every contract created, deleted or changed in its audit "
             "log that day.",
    )
    contracts_change_recipient_ids = fields.Many2many(
        related='company_id.contracts_change_recipient_ids', readonly=False,
    )
    # Not a system parameter: read from and written to the summary job's own
    # next run, so the job is the one place the time lives, and moving it
    # under Scheduled Actions shows up here too.
    contracts_change_summary_time = fields.Float(
        string='Summary Time', default=DEFAULT_SUMMARY_TIME,
        help="Time of day the summary goes out, in your own timezone.",
    )

    # ── Reminder scheduled action ─────────────────────────────────
    def _get_reminder_cron(self):
        """The reminder cron, found whether it is currently on or off."""
        return self.sudo().with_context(active_test=False).env.ref(
            'contracts.ir_cron_contract_expiry_reminders',
            raise_if_not_found=False,
        )

    # ── Change summary scheduled action ───────────────────────────
    def _get_summary_cron(self):
        """The daily change summary cron, found whether it is on or off."""
        return self.sudo().with_context(active_test=False).env.ref(
            'contracts.ir_cron_contract_daily_changes',
            raise_if_not_found=False,
        )

    def _user_tz(self):
        return pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')

    @api.model
    def get_values(self):
        values = super().get_values()
        summary = self._get_summary_cron()
        if summary and summary.nextcall:
            local = pytz.utc.localize(summary.nextcall).astimezone(self._user_tz())
            values['contracts_change_summary_time'] = local.hour + local.minute / 60
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
        self._set_summary_time()

    def _set_summary_time(self):
        """Move the summary job's next run to the time picked, today if that
        time is still ahead, otherwise tomorrow. Left alone when the time is
        unchanged, so saving other settings never shifts it a day."""
        summary = self._get_summary_cron()
        if not summary:
            return
        minutes = round(self.contracts_change_summary_time * 60)
        if not 0 <= minutes < 24 * 60:
            raise ValidationError(_("The summary time has to be between 00:00 and 23:59."))
        tz = self._user_tz()
        # The database's clock, which the scheduler itself goes by.
        now = pytz.utc.localize(self.env.cr.now()).astimezone(tz)
        current = pytz.utc.localize(summary.nextcall).astimezone(tz) if summary.nextcall else None
        if current and current.hour * 60 + current.minute == minutes:
            return
        target = now.replace(tzinfo=None, hour=minutes // 60, minute=minutes % 60,
                             second=0, microsecond=0)
        if target <= now.replace(tzinfo=None):
            target += timedelta(days=1)
        summary.nextcall = tz.localize(target).astimezone(pytz.utc).replace(tzinfo=None)
