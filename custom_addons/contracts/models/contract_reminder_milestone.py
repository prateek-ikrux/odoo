# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ContractReminderMilestone(models.Model):
    """One choice for when an expiry reminder can go out, shown as a chip.

    Only the picker's vocabulary: which of these are switched on is still the
    'contracts.reminder_days' system parameter the reminder cron reads, so the
    settings screen translates between the two.
    """
    _name = 'contracts.reminder.milestone'
    _description = 'Expiry Reminder Milestone'
    _order = 'days desc'
    _rec_name = 'name'

    days = fields.Integer(string='Days Before End Date', required=True)
    name = fields.Char(compute='_compute_name', store=True)
    # Same scale as the accent on the reminder email: red is urgent.
    color = fields.Integer(compute='_compute_color')

    _days_uniq = models.Constraint(
        'unique (days)',
        "That number of days is already in the list.",
    )
    _days_positive = models.Constraint(
        'CHECK (days > 0)',
        "A reminder has to go out at least one day before the end date.",
    )

    @api.depends('days')
    def _compute_name(self):
        for rec in self:
            rec.name = _('1 day') if rec.days == 1 else _('%s days', rec.days)

    @api.depends('days')
    def _compute_color(self):
        for rec in self:
            rec.color = 1 if rec.days <= 7 else 2 if rec.days <= 30 else 4

    @api.model
    def name_create(self, name):
        """Typing a number in the picker adds it as a chip: '10', '10 days'
        and ' 10d ' all mean ten days, and one already listed is reused."""
        match = re.fullmatch(r'\s*(\d+)\s*(d|day|days)?\s*', name or '', re.IGNORECASE)
        if not match or int(match.group(1)) <= 0:
            raise ValidationError(
                _("Type a whole number of days above zero, for example 10."))
        record = self._get_or_create(int(match.group(1)))
        return record.id, record.display_name

    @api.model
    def _get_or_create(self, days):
        record = self.search([('days', '=', days)], limit=1)
        return record or self.create({'days': days})
