# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Fallbacks for the system parameters the settings screen writes.
DEFAULT_REMINDER_HOURS = '48,24,12,1'
PARAM_HOURS = 'crm_meeting_reminders.hours'
PARAM_CC = 'crm_meeting_reminders.cc_emails'
PARAM_FROM = 'crm_meeting_reminders.email_from'


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    crm_reminder_sent_hours = fields.Integer(
        string='Last Reminder', readonly=True, copy=False,
        help="Hour milestone of the most recent reminder sent for this "
             "meeting. Zero means none has been sent yet. Reset whenever the "
             "meeting is moved, so rescheduling starts the sequence over.",
    )
    crm_reminder_last_sent = fields.Datetime(
        string='Reminder Sent On', readonly=True, copy=False,
    )

    def write(self, vals):
        if 'start' in vals:
            # A meeting that moves has to be warned about again against its new
            # time. setdefault keeps the cron's own write - which sets the
            # marker and never touches start - out of the way.
            vals.setdefault('crm_reminder_sent_hours', 0)
            vals.setdefault('crm_reminder_last_sent', False)
        return super().write(vals)

    # ── Configuration ─────────────────────────────────────────────
    @api.model
    def _get_meeting_reminder_hours(self):
        """Hour milestones a reminder goes out on, most distant first."""
        raw = self.env['ir.config_parameter'].sudo().get_param(
            PARAM_HOURS, DEFAULT_REMINDER_HOURS)
        hours = set()
        for chunk in (raw or '').split(','):
            chunk = chunk.strip()
            if chunk.isdigit() and int(chunk) > 0:
                hours.add(int(chunk))
        return sorted(hours, reverse=True)

    @api.model
    def _get_meeting_reminder_cc(self):
        """Addresses copied on every reminder, involved in the meeting or not."""
        raw = self.env['ir.config_parameter'].sudo().get_param(PARAM_CC, '')
        return ','.join(e.strip() for e in (raw or '').split(',') if e.strip())

    @api.model
    def _get_meeting_reminder_from(self):
        """Sending address, or '' to leave it to the usual Odoo fallbacks."""
        return (self.env['ir.config_parameter'].sudo().get_param(
            PARAM_FROM, '') or '').strip()

    def _get_reminder_attendee_emails(self):
        """Attendees still expected to turn up, as a comma-separated list."""
        self.ensure_one()
        emails = []
        for attendee in self.attendee_ids:
            if attendee.state == 'declined':
                continue
            email = (attendee.email or '').strip()
            if email and email not in emails:
                emails.append(email)
        return ','.join(emails)

    def _reminder_attendee_names(self):
        """Who is still expected, for the body of the reminder."""
        self.ensure_one()
        names = [
            attendee.common_name or attendee.email or ''
            for attendee in self.attendee_ids
            if attendee.state != 'declined'
        ]
        return ', '.join(n for n in names if n)

    # ── Scheduled action ──────────────────────────────────────────
    @api.model
    def _cron_send_meeting_reminders(self):
        """Warn before a meeting behind an opportunity starts.

        The milestone sent is the most urgent one reached, and only if it beats
        what already went out, so a repeated run is a no-op and a gap in the
        schedule still produces one warning rather than a burst of stale ones.
        """
        hours = self._get_meeting_reminder_hours()
        if not hours:
            _logger.warning(
                "CRM meeting reminders: no milestones in '%s'; skipping run.",
                PARAM_HOURS)
            return True

        template = self.env.ref(
            'crm_meeting_reminders.mail_template_crm_meeting_reminder',
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning(
                "CRM meeting reminders: mail template is missing; skipping run.")
            return True

        now = fields.Datetime.now()
        cc = self._get_meeting_reminder_cc()
        email_from = self._get_meeting_reminder_from()

        # The widest milestone bounds the candidate set; the per-record check
        # below picks the milestone that actually applies.
        events = self.search([
            ('opportunity_id', '!=', False),
            ('start', '>', now),
            ('start', '<=', now + timedelta(hours=max(hours))),
        ])

        for event in events:
            hours_left = (event.start - now).total_seconds() / 3600.0
            reached = [h for h in hours if hours_left <= h]
            if not reached:
                continue
            milestone = min(reached)
            if event.crm_reminder_sent_hours \
                    and milestone >= event.crm_reminder_sent_hours:
                # This milestone, or a less urgent one, already went out.
                continue

            to = event._get_reminder_attendee_emails()
            values = {}
            if to:
                values['email_to'] = to
                if cc:
                    values['email_cc'] = cc
            elif cc:
                # Nobody left to notify on the meeting itself, but the standing
                # list still wants to know it is coming up.
                values['email_to'] = cc
            else:
                continue
            if email_from:
                values['email_from'] = email_from
                # The meeting is the organiser's, so replies belong to them
                # even when the mail is sent from a service mailbox.
                values['reply_to'] = event.user_id.email_formatted or email_from

            try:
                # A savepoint per meeting: one bad record must not abort the
                # run, nor leave the cursor unusable for the ones after it.
                with self.env.cr.savepoint():
                    template.with_context(reminder_hours=milestone).send_mail(
                        event.id, email_values=values, force_send=False,
                    )
                    event.write({
                        'crm_reminder_sent_hours': milestone,
                        'crm_reminder_last_sent': now,
                    })
            except Exception:
                _logger.exception(
                    "CRM meeting reminder failed for meeting %s (id %s).",
                    event.name, event.id,
                )
        return True
