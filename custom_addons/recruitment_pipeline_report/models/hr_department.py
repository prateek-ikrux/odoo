# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class HrDepartment(models.Model):
    # Departments are the clients here.
    _name = 'hr.department'
    _inherit = ['hr.department', 'recruitment.notify.mixin']
    _rn_kind = 'client'
    _rn_action = 'hr.hr_department_kanban_action'

    # Recorded in the audit log, so a change to any of them is mailed.
    name = fields.Char(tracking=True)
    parent_id = fields.Many2one(tracking=True)
    active = fields.Boolean(tracking=True)

    x_poc_contact_count = fields.Integer(
        string='POC Contacts',
        compute='_compute_poc_contact_count',
    )

    def _compute_poc_contact_count(self):
        partner_model = self.env['res.partner']
        for dept in self:
            dept.x_poc_contact_count = partner_model.search_count([
                ('x_client_department_id', '=', dept.id),
            ])

    def action_view_poc_contacts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'POC Contacts',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('x_client_department_id', '=', self.id)],
            'context': {
                'default_x_client_department_id': self.id,
                'search_default_x_client_department_id': self.id,
            },
        }

    # ── Email notifications ───────────────────────────────────────
    def _rn_assigned_users(self):
        """The client's Manager, through the user linked to that employee."""
        return self.manager_id.user_id

    def _rn_details(self):
        self.ensure_one()
        dept = self.sudo()
        jobs = self.env['hr.job'].sudo().with_context(active_test=False).search(
            [('department_id', '=', dept.id)])
        return {
            'name': dept.name or '',
            'parent': dept.parent_id.display_name or '',
            'manager': dept.manager_id.name or '',
            'roles': len(jobs.filtered('active')),
            'open_roles': len(jobs.filtered(lambda j: j.active and j.x_role_status != 'closed')),
            'pocs': dept.x_poc_contact_count,
            'created_by': dept.create_uid.name or '',
            'created_on': self._rn_local_date(dept.create_date),
        }

    def _rn_notify(self, event, changes=None):
        if not self._rn_enabled('client'):
            return
        for dept in self:
            dept._rn_send('recruitment_pipeline_report.mail_template_rp_client',
                          dept._rn_partners('client'),
                          {'rn_event': event, 'rn_changes': changes or []})

    @api.model_create_multi
    def create(self, vals_list):
        departments = super().create(vals_list)
        departments._rn_notify('created')
        return departments

    def _message_track(self, fields_iter, initial_values_dict):
        """Mail whatever the audit log just recorded about a client."""
        tracking = super()._message_track(fields_iter, initial_values_dict)
        for dept in self:
            changes = tracking.get(dept.id, (None, None))[0]
            if changes:
                dept._rn_notify('updated', dept._rn_format_changes(
                    changes, initial_values_dict[dept.id]))
        return tracking

    def unlink(self):
        if len(self) == 1:
            subject = _('Client deleted: %s', self.name)
        else:
            subject = _('%(count)s clients deleted: %(names)s',
                        count=len(self), names=', '.join(self[:3].mapped('name')))
        self._rn_send_deleted('recruitment_pipeline_report.mail_template_rp_client', subject)
        return super().unlink()
