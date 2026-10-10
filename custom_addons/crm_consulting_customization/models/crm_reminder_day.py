# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CrmReminderDay(models.Model):
    """A number of days, shown as a chip in the CRM email settings.

    Only the pickers' vocabulary, shared by both reminder kinds: which days
    are switched on for each is held in a system parameter the reminder crons
    read, and the settings screen translates between the two.
    """
    _name = 'crm.reminder.day'
    _description = 'CRM Reminder Day'
    _order = 'days'
    _rec_name = 'name'

    days = fields.Integer(string='Days', required=True)
    name = fields.Char(compute='_compute_name', store=True)

    _days_uniq = models.Constraint(
        'unique (days)',
        "That number of days is already in the list.",
    )
    _days_positive = models.Constraint(
        'CHECK (days > 0)',
        "A reminder needs at least one day.",
    )

    @api.depends('days')
    def _compute_name(self):
        for rec in self:
            rec.name = _('1 day') if rec.days == 1 else _('%s days', rec.days)

    @api.model
    def name_create(self, name):
        """Typing a number in a picker adds it as a chip: '10', '10 days'
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
