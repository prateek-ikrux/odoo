# -*- coding: utf-8 -*-
"""Email notifications shared by clients (hr.department), roles (hr.job) and
candidates (hr.applicant).

Each kind of email has its own settings under Recruitment > Configuration >
Settings: a switch, whether the record's creator and its assigned people
receive it, and anyone else picked by name. The switches are system
parameters named recruitment_pipeline.<kind>_notify[_creator|_assigned];
the people picked live on the company.
"""
import logging

from odoo import _, api, fields, models
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

PARAM_PREFIX = 'recruitment_pipeline.'
STUCK_REMINDER_DAYS_PARAM = PARAM_PREFIX + 'stuck_reminder_days'
DEFAULT_STUCK_REMINDER_DAYS = '3,7,14'

# The company field holding the people picked for each kind of email.
RECIPIENT_FIELDS = {
    'client': 'x_rp_client_recipient_ids',
    'role': 'x_rp_role_recipient_ids',
    'stuck': 'x_rp_stuck_recipient_ids',
}


class RecruitmentNotifyMixin(models.AbstractModel):
    _name = 'recruitment.notify.mixin'
    _description = 'Recruitment Email Notification Helpers'

    # Which settings this model's emails read: 'client', 'role' or 'stuck'.
    _rn_kind = None
    # The action a "View" button in the email opens the record through.
    _rn_action = None

    # ── Settings ──────────────────────────────────────────────────
    @api.model
    def _rn_param(self, suffix):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM_PREFIX + suffix)

    @api.model
    def _rn_enabled(self, kind):
        return bool(self._rn_param(f'{kind}_notify'))

    def _rn_assigned_users(self):
        """The people assigned to this record. Overridden per model."""
        return self.env['res.users']

    def _rn_partners(self, kind):
        """Who receives this record's email of the given kind: the creator
        and the assigned people when the settings say so, plus anyone picked
        by name - those of them who are active and have an address."""
        users = self.env['res.users']
        if self._rn_param(f'{kind}_notify_creator'):
            users |= self.sudo().create_uid
        if self._rn_param(f'{kind}_notify_assigned'):
            for rec in self:
                users |= rec.sudo()._rn_assigned_users()
        users |= self.env.company.sudo()[RECIPIENT_FIELDS[kind]]
        users = users.filtered(lambda u: u.active and u.email and not u.share)
        return users.partner_id

    # ── Formatting ────────────────────────────────────────────────
    @api.model
    def _rn_date(self, value, pattern='d MMM y'):
        return format_date(self.env, value, date_format=pattern) if value else ''

    @api.model
    def _rn_local_date(self, value, pattern='d MMM y'):
        """A stored UTC datetime, as a date in the reader's timezone."""
        if not value:
            return ''
        return self._rn_date(fields.Datetime.context_timestamp(self, value), pattern)

    @api.model
    def _rn_number(self, value):
        """A number as entered: 1200000 stays 1200000 (:g would give
        1.2e+06), and 12.50 drops its trailing zero to 12.5."""
        return f'{value or 0:f}'.rstrip('0').rstrip('.')

    def _rn_changed_by(self):
        # Crons run as the superuser; naming OdooBot would only puzzle.
        return _('Automatic update') if self.env.user._is_superuser() else self.env.user.name

    def _rn_url(self):
        self.ensure_one()
        return f'{self.get_base_url()}/odoo/action-{self._rn_action}/{self.id}'

    def _rn_format_changes(self, changes, initial_values):
        """Old and new value of each changed field, as display text, in the
        order the fields are declared."""
        self.ensure_one()
        return [
            {
                'field': self._fields[fname]._description_string(self.env),
                'old': self._rn_format_value(fname, initial_values.get(fname)),
                'new': self._rn_format_value(fname, self[fname]),
            }
            for fname in self._fields if fname in changes
        ]

    def _rn_format_value(self, fname, value):
        field = self._fields[fname]
        empty = '—'
        if field.type == 'boolean':
            return _('Yes') if value else _('No')
        if field.type in ('integer', 'float', 'monetary'):
            return self._rn_number(value)
        if value is None or value is False or value == '':
            return empty
        if field.type == 'selection':
            return dict(field._description_selection(self.env)).get(value, value)
        if field.type in ('many2one', 'many2many', 'one2many'):
            return ', '.join(value.sudo().mapped('display_name')) or empty
        if field.type == 'date':
            return self._rn_date(value)
        if field.type == 'datetime':
            return self._rn_local_date(value)
        if field.type == 'html':
            return _('(updated)')
        return str(value)

    # ── Sending ───────────────────────────────────────────────────
    def _rn_send(self, template_xmlid, partners, values):
        """Queue one email about this record. Never raises: an email that
        cannot be built is logged and dropped, and the change it reports on
        goes through regardless."""
        self.ensure_one()
        if not partners:
            return False
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            _logger.warning("Recruitment notification: mail template %s is missing.", template_xmlid)
            return False
        try:
            with self.env.cr.savepoint():
                template.sudo().with_context(
                    rn_url=self._rn_url(),
                    rn_changed_by=self._rn_changed_by(),
                    rn_details=self._rn_details(),
                    **values,
                ).send_mail(
                    self.id,
                    email_values={'recipient_ids': [(6, 0, partners.ids)]},
                    force_send=False,
                )
            return True
        except Exception:
            _logger.exception("Recruitment notification %s failed for %s %s.",
                              template_xmlid, self._name, self.id)
            return False

    def _rn_send_deleted(self, template_xmlid, subject):
        """One email listing every record about to be deleted.

        Built before the delete, while the records can still be read, and not
        linked to them: mail.thread removes every message tied to a record it
        deletes, which would take a queued email with it. If the delete itself
        fails, the transaction rolls the email back too.
        """
        kind = self._rn_kind
        if not self or not self._rn_enabled(kind):
            return
        partners = self._rn_partners(kind)
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not partners or not template:
            return
        try:
            with self.env.cr.savepoint():
                first = self[0]
                template = template.sudo().with_context(
                    rn_event='deleted',
                    rn_subject=subject,
                    rn_deleted=[rec._rn_details() for rec in self],
                    rn_changed_by=self._rn_changed_by(),
                    rn_details=first._rn_details(),
                )
                self.env['mail.mail'].sudo().create({
                    'subject': template._render_field('subject', first.ids)[first.id],
                    'body_html': template._render_field('body_html', first.ids)[first.id],
                    'recipient_ids': [(6, 0, partners.ids)],
                    'auto_delete': True,
                })
        except Exception:
            # A notification must never block the deletion it reports on.
            _logger.exception("Recruitment deletion notification failed for %s %s.",
                              self._name, self.ids)

    def _rn_details(self):
        """The record's key facts, formatted for its emails. Overridden."""
        return {}
