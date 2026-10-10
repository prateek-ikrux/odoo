# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RecruitmentReminderDay(models.Model):
    """A number of days, shown as a chip in the stuck-candidate settings.

    Only the picker's vocabulary: which days are switched on is held in the
    'recruitment_pipeline.stuck_reminder_days' system parameter the reminder
    cron reads, and the settings screen translates between the two.
    """
    _name = 'recruitment.reminder.day'
    _description = 'Recruitment Reminder Day'
    _order = 'days'
    _rec_name = 'name'

    days = fields.Integer(string='Days', required=True)
    name = fields.Char(compute='_compute_name', store=True)
    # Same scale as the reminder email: red once it has gone two weeks.
    color = fields.Integer(compute='_compute_color')

    _days_uniq = models.Constraint('unique (days)', "That number of days is already in the list.")
    _days_positive = models.Constraint('CHECK (days > 0)', "A reminder needs at least one day.")

    @api.depends('days')
    def _compute_name(self):
        for rec in self:
            rec.name = _('1 day') if rec.days == 1 else _('%s days', rec.days)

    @api.depends('days')
    def _compute_color(self):
        for rec in self:
            rec.color = 1 if rec.days >= 14 else 2 if rec.days >= 5 else 4

    @api.model
    def name_create(self, name):
        """Typing a number in the picker adds it as a chip: '10', '10 days'
        and ' 10d ' all mean ten days, and one already listed is reused."""
        match = re.fullmatch(r'\s*(\d+)\s*(d|day|days)?\s*', name or '', re.IGNORECASE)
        if not match or int(match.group(1)) <= 0:
            raise ValidationError(_("Type a whole number of days above zero, for example 10."))
        record = self._get_or_create(int(match.group(1)))
        return record.id, record.display_name

    @api.model
    def _get_or_create(self, days):
        record = self.search([('days', '=', days)], limit=1)
        return record or self.create({'days': days})
