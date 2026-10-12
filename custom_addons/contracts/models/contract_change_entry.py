# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

EVENT_SELECTION = [
    ('created', 'Created'),
    ('updated', 'Updated'),
    ('deleted', 'Deleted'),
]


class ContractChangeEntry(models.Model):
    """A contract created, changed or deleted, waiting for the end-of-day
    email. Deleted once that email has been written."""
    _name = 'contracts.change.entry'
    _description = 'Contract Change Awaiting the Daily Email'
    _order = 'id'

    event = fields.Selection(EVENT_SELECTION, required=True)
    res_id = fields.Integer()
    record_name = fields.Char()
    kind = fields.Char()  # MSA or SOW
    url = fields.Char()
    changed_by = fields.Char()
    # [{'field', 'old', 'new'}] for an update, as the audit log shows it.
    changes = fields.Json()
    # [[label, value]] describing the contract, for one created or deleted.
    details = fields.Json()

    @api.model
    def _cron_send_daily_changes(self):
        """Email everything queued since the last run as one summary, grouped
        by contract. Runs once a day, at the end of it. Nothing is sent on a
        day without changes."""
        if not self.env['ir.config_parameter'].sudo().get_param('contracts.change_notify'):
            # Queued while it was on and never sent: dropped, rather than
            # arriving as a surprise backlog the day it is switched on again.
            self.search([]).unlink()
            return True
        entries = self.search([])
        if not entries:
            return True
        template = self.env.ref('contracts.mail_template_contract_daily_changes',
                                raise_if_not_found=False)
        if not template:
            _logger.warning("Contract daily changes: mail template is missing; kept for the next run.")
            return True
        users = self.env.company.sudo().contracts_change_recipient_ids.filtered(
            lambda u: u.active and u.email)
        for user in users:
            try:
                with self.env.cr.savepoint():
                    template.sudo().with_context(
                        contracts_daily=entries._get_daily_values(user),
                    ).send_mail(user.partner_id.id, email_values={
                        'recipient_ids': [(6, 0, user.partner_id.ids)],
                    }, force_send=False)
            except Exception:
                _logger.exception("Contract daily changes failed for user %s.", user.id)
        entries.unlink()
        return True

    def _get_daily_values(self, user):
        """The queued changes, one block per contract in the order they were
        first touched, with times in the reader's own timezone."""
        as_user = self.with_context(tz=user.tz or 'UTC')
        labels = dict(EVENT_SELECTION)
        contracts = {}
        for entry in self:
            block = contracts.setdefault(entry.res_id, {
                'name': entry.record_name,
                'kind': entry.kind,
                'url': '',
                'events': [],
            })
            # The latest name and link win: a contract renamed during the day
            # shows as it is now, and one deleted has no link left to follow.
            block['name'] = entry.record_name
            block['url'] = entry.url
            block['events'].append({
                'event': entry.event,
                'label': labels[entry.event],
                'time': fields.Datetime.context_timestamp(as_user, entry.create_date).strftime('%H:%M'),
                'changed_by': entry.changed_by or '',
                'changes': entry.changes or [],
                'details': entry.details or [],
            })
        first = fields.Datetime.context_timestamp(as_user, self[0].create_date)
        counts = {event: len(self.filtered(lambda e: e.event == event)) for event in labels}
        return {
            'date': format_date(self.env, first, date_format='EEEE, d MMMM y'),
            'contracts': list(contracts.values()),
            'count': len(contracts),
            'created': counts['created'],
            'updated': counts['updated'],
            'deleted': counts['deleted'],
            'subject': _('Contracts: %(count)s contract%(s)s changed today', count=len(contracts),
                         s='' if len(contracts) == 1 else 's'),
        }
