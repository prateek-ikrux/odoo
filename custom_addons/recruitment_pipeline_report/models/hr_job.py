# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from .pipeline_constants import ROLE_STATUS_SELECTION, SUB_STATUS_SELECTION


# What can still be written on a closed role. Role Status and its remarks so
# it can be reopened; active so it can be archived; the rest because Odoo
# itself writes them: starring a role as a favourite, and the hiring target
# moving when one of its candidates is hired or un-hired.
CLOSED_ROLE_WRITABLE = {
    'x_role_status', 'x_sub_status', 'active',
    'favorite_user_ids', 'is_favorite', 'no_of_recruitment',
    'is_published', 'website_published',
}


class HrJob(models.Model):
    _name = 'hr.job'
    _inherit = ['hr.job', 'recruitment.notify.mixin']
    _rn_kind = 'role'
    _rn_action = 'hr_recruitment.action_hr_job_config'

    department_id = fields.Many2one(string='Client')

    # Recorded in the audit log, so a change to any of them is mailed.
    name = fields.Char(tracking=True)
    no_of_recruitment = fields.Integer(tracking=True)
    active = fields.Boolean(tracking=True)

    x_employment_type = fields.Selection(
        selection=[
            ('fte',             'FTE'),
            ('consulting',      'Consulting'),
            ('fte_consulting',  'FTE/Consulting'),
        ],
        string='Employment Type',
        tracking=True,
    )

    x_poc_id = fields.Many2one(
        'res.partner',
        string='Point of Contact (POC)',
        domain="[('x_client_department_id', '=', department_id)]",
        help='External client contact who handles this job position.',
        tracking=True,
    )

    x_role_status = fields.Selection(
        selection=ROLE_STATUS_SELECTION,
        string='Role Status',
        default='active',
        tracking=True,
    )

    x_sub_status = fields.Selection(
        selection=SUB_STATUS_SELECTION,
        string='Role Status Remarks',
        tracking=True,
    )

    # ── New fields ────────────────────────────────────────────────
    x_req_id_available = fields.Selection(
        selection=[('yes', 'Yes'), ('no', 'No')],
        string='Req ID Available?',
        default='yes',
        help='Select "Yes" if you already have a Requisition ID to enter manually. '
             'Select "No" to have one generated automatically when the job position is saved '
             '(format: REQ-2026-00001).',
    )

    x_req_id = fields.Char(
        string='Req ID',
        copy=False,
        help='Requisition ID for this job position. Enter manually (e.g. REQ-2024-001) '
             'if available, or set "Req ID Available?" to "No" to auto-generate one on save.',
        tracking=True,
    )

    _x_req_id_uniq = models.Constraint(
        'unique (x_req_id)',
        'Req ID must be unique! This Req ID is already assigned to another job position.',
    )

    # Deprecated alias — kept only so existing ir.ui.view records that still
    # reference x_rec_id pass ORM validation during the upgrade. Odoo will
    # overwrite those view records with the new XML (using x_req_id) as part
    # of this same upgrade. Safe to remove in a future version.
    x_rec_id = fields.Char(
        related='x_req_id',
        string='Req ID (deprecated)',
        store=False,
        readonly=True,
    )

    x_min_experience = fields.Integer(
        string='Min Experience (Yrs)',
        default=0,
        tracking=True,
    )

    x_max_experience = fields.Integer(
        string='Max Experience (Yrs)',
        default=0,
        tracking=True,
    )

    @api.constrains('x_min_experience', 'x_max_experience')
    def _check_experience_range(self):
        for rec in self:
            if rec.x_min_experience < 0:
                raise ValidationError('Min Experience (Yrs) cannot be negative.')
            if rec.x_max_experience < 0:
                raise ValidationError('Max Experience (Yrs) cannot be negative.')
            # Max = 0 is treated as "not specified" (the field's default),
            # so it's skipped here rather than flagged as Min > Max.
            if rec.x_max_experience and rec.x_min_experience > rec.x_max_experience:
                raise ValidationError(
                    'Min Experience (Yrs) cannot be greater than Max Experience (Yrs).'
                )

    x_location_ids = fields.Many2many(
        'recruitment.city',
        'hr_job_city_rel',
        'job_id', 'city_id',
        string='Job Locations',
        tracking=True,
    )

    x_skill_ids = fields.Many2many(
        'recruitment.skill',
        'hr_job_skill_rel',
        'job_id', 'skill_id',
        string='Required Skills',
        tracking=True,
    )

    x_role_received_date = fields.Date(
        string='Role Received from Client',
        tracking=True,
    )

    x_role_opened_date = fields.Date(
        string='Role Opened to Team',
        tracking=True,
    )

    x_display_name = fields.Char(
        string='Job Position',
        compute='_compute_display_name_with_type',
        store=True,
    )

    x_recruiter_ids = fields.Many2many(
        'res.users',
        'hr_job_recruiter_rel',
        'job_id', 'user_id',
        string='Recruiters',
        domain="[('share', '=', False)]",
        tracking=True,
    )

    x_recruiter_team_id = fields.Many2one(
        'recruiter.team',
        string='Recruiter Group',
        help='Pick a saved Recruiter Group to fill Recruiters and Team Lead in one step. '
             'If you edit Recruiters afterwards, the Recruiter Group link is cleared '
             'automatically (the job keeps whichever recruiters are listed).',
        tracking=True,
    )

    @api.onchange('x_recruiter_team_id')
    def _onchange_x_recruiter_team_id(self):
        if self.x_recruiter_team_id:
            self.x_recruiter_ids = self.x_recruiter_team_id.member_ids
            self.user_id = self.x_recruiter_team_id.team_lead_id

    @api.onchange('x_recruiter_ids')
    def _onchange_x_recruiter_ids_detach_team(self):
        # If recruiters no longer match the linked group's members, detach
        # the group link rather than blocking the save — the group was a
        # one-time fill helper, not a permanent constraint.
        if self.x_recruiter_team_id and set(self.x_recruiter_ids.ids) != set(self.x_recruiter_team_id.member_ids.ids):
            self.x_recruiter_team_id = False



    x_budget_lpa = fields.Float(
        string='Budget (LPA)',
        help='Approved budget for FTE roles in Lakhs Per Annum.',
        tracking=True,
    )

    x_bill_rate_lpm = fields.Float(
        string='Bill Rate (LPM)',
        help='Agreed bill rate for Consulting roles in Lakhs Per Month.',
        tracking=True,
    )

    # @api.constrains('x_budget_lpa', 'x_bill_rate_lpm')
    # def _check_budget_bill_rate_not_negative(self):
    #     for rec in self:
    #         if rec.x_budget_lpa < 0:
    #             raise ValidationError('Budget (LPA) cannot be negative.')
    #         if rec.x_bill_rate_lpm < 0:
    #             raise ValidationError('Bill Rate (LPM) cannot be negative.')

    @api.constrains('x_budget_lpa', 'x_bill_rate_lpm', 'x_employment_type')
    def _check_budget_bill_rate_positive(self):
        for rec in self:
            if rec.x_employment_type in ('fte', 'fte_consulting') and rec.x_budget_lpa <= 0:
                raise ValidationError('Budget (LPA) must be greater than zero for FTE roles.')
            if rec.x_employment_type == 'consulting' and rec.x_bill_rate_lpm <= 0:
                raise ValidationError('Bill Rate (LPM) must be greater than zero for Consulting roles.')

    # ── Create / write hooks ──────────────────────────────────────

    def _generate_unique_req_id(self):
        """Generate a unique Req ID using the ir.sequence, in the format
        REQ-2026-00001. Retries on the rare chance the sequence-issued
        number is already in use (defense-in-depth on top of the
        x_req_id_uniq SQL constraint), so every generated value is
        guaranteed unique."""
        Sequence = self.env['ir.sequence']
        for _attempt in range(100):
            candidate = Sequence.next_by_code('hr.job.x_req_id')
            if not candidate:
                raise ValidationError(
                    'Could not generate a Req ID automatically: the '
                    '"Job Req ID" sequence is missing. Please contact your administrator.'
                )
            if not self.env['hr.job'].sudo().search_count([('x_req_id', '=', candidate)]):
                return candidate
        raise ValidationError('Could not generate a unique Req ID. Please try again.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('x_req_id_available') == 'no' and not vals.get('x_req_id'):
                vals['x_req_id'] = self._generate_unique_req_id()
        jobs = super().create(vals_list)
        for job in jobs:
            if job.x_recruiter_team_id:
                continue  # group owns both fields; nothing to reconcile
            # Keep user_id in sync with recruiter list
            if job.x_recruiter_ids and not job.user_id:
                job.user_id = job.x_recruiter_ids[0]
            elif job.user_id and not job.x_recruiter_ids:
                job.x_recruiter_ids = [(4, job.user_id.id)]
        return jobs

    def _check_closed_role_lock(self, vals):
        """A closed role is read-only until it is reopened, so nothing about
        it changes by accident. Reopening it in the same save is allowed, and
        Odoo's own sudo writes are left alone."""
        if self.env.su or vals.get('x_role_status', 'closed') != 'closed':
            return
        locked = set(vals) - CLOSED_ROLE_WRITABLE
        closed = self.filtered(lambda job: job.x_role_status == 'closed')
        if locked and closed:
            raise ValidationError(_(
                '%(roles)s is closed, so it cannot be changed. Set its Role Status '
                'back to an open status first if the role is being reopened.',
                roles=', '.join(closed[:3].mapped('display_name')),
            ))

    def write(self, vals):
        self._check_closed_role_lock(vals)
        # Auto-generate Req ID per-record when "Req ID Available?" is set to
        # "No" and no Req ID was explicitly supplied in this write. Handled
        # record-by-record so each job that needs one gets its own unique
        # value (relevant when writing on multiple jobs at once).
        wants_auto_req_id = vals.get('x_req_id_available') == 'no' and not vals.get('x_req_id')
        if wants_auto_req_id:
            for job in self:
                job_vals = vals
                if not job.x_req_id:
                    job_vals = dict(vals, x_req_id=self._generate_unique_req_id())
                super(HrJob, job).write(job_vals)
            res = True
        else:
            res = super().write(vals)

        if 'x_recruiter_ids' in vals:
            for job in self:
                if job.x_recruiter_team_id:
                    continue  # group owns both fields; nothing to reconcile
                if job.x_recruiter_ids:
                    if job.user_id not in job.x_recruiter_ids:
                        job.user_id = job.x_recruiter_ids[0]
                else:
                    job.user_id = False
        elif 'user_id' in vals:
            for job in self:
                if job.x_recruiter_team_id:
                    continue  # group owns both fields; nothing to reconcile
                if job.user_id and job.user_id not in job.x_recruiter_ids:
                    job.x_recruiter_ids = [(4, job.user_id.id)]

        # Keep already-linked applicants' Client (department_id) in sync
        # whenever the Job Position's own Client changes. Without this,
        # an applicant only picks up the job's Client at the moment
        # job_id is set on it (see hr_applicant.py create/write); if the
        # Client is added or corrected on the job afterwards, existing
        # applicants would otherwise be left with a stale or blank Client.
        if 'department_id' in vals:
            for job in self:
                applicants = self.env['hr.applicant'].search([('job_id', '=', job.id)])
                if applicants:
                    applicants.write({'department_id': job.department_id.id})

        return res

    # ── Display name computation ──────────────────────────────────

    def _job_display_label(self, req_id, name, department, employment_type,
                           min_exp, max_exp):
        """
        Format: [JOB0001] Infosys - Python Developer | FTE | 2-4 Yrs
        """
        emp_labels = {'fte': 'FTE', 'consulting': 'Consulting', 'fte_consulting': 'FTE/Consulting'}
        prefix = f'[{req_id}] ' if req_id else ''
        client = department.display_name if department else ''
        role   = name or ''
        emp    = emp_labels.get(employment_type, '')
        if min_exp and not max_exp:
            exp = f'{min_exp}+ Yrs'
        elif min_exp or max_exp:
            exp = f'{min_exp}-{max_exp} Yrs'
        else:
            exp = ''

        core  = f'{client} - {role}' if client else role
        label = prefix + core
        if emp:
            label += f' | {emp}'
        if exp:
            label += f' | {exp}'
        return label

    @api.depends('name', 'department_id', 'x_employment_type',
                 'x_req_id', 'x_min_experience', 'x_max_experience')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec._job_display_label(
                rec.x_req_id, rec.name, rec.department_id,
                rec.x_employment_type, rec.x_min_experience, rec.x_max_experience,
            )

    @api.depends('name', 'department_id', 'x_employment_type',
                 'x_req_id', 'x_min_experience', 'x_max_experience')
    def _compute_display_name_with_type(self):
        for rec in self:
            rec.x_display_name = rec._job_display_label(
                rec.x_req_id, rec.name, rec.department_id,
                rec.x_employment_type, rec.x_min_experience, rec.x_max_experience,
            )

    def create_action(self):
        """After creating a Job Position, redirect to its config/form page
        instead of the default applicant-stage kanban view."""
        self.ensure_one()
        form_view_id = self.env.ref('hr.view_hr_job_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': self.display_name or self.name,
            'res_model': 'hr.job',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(form_view_id, 'form')],
            'target': 'current',
        }

    # ── Email notifications ───────────────────────────────────────
    def _rn_assigned_users(self):
        """The role team: its Recruitment Manager and its Recruiters."""
        return self.user_id | self.x_recruiter_ids

    def _rn_details(self):
        self.ensure_one()
        job = self.sudo()
        applicants = self.env['hr.applicant'].sudo().search([('job_id', '=', job.id)])
        if job.x_employment_type == 'consulting':
            commercial = _('%s LPM', f'{job.x_bill_rate_lpm:g}') if job.x_bill_rate_lpm else ''
        else:
            commercial = _('%s LPA', f'{job.x_budget_lpa:g}') if job.x_budget_lpa else ''
        if job.x_min_experience and not job.x_max_experience:
            experience = _('%s+ yrs', job.x_min_experience)
        elif job.x_min_experience or job.x_max_experience:
            experience = _('%(min)s-%(max)s yrs', min=job.x_min_experience, max=job.x_max_experience)
        else:
            experience = ''
        return {
            'name': job.name or '',
            'req_id': job.x_req_id or '',
            'client': job.department_id.name or '',
            'poc': job.x_poc_id.name or '',
            'employment_type': self._rn_format_value('x_employment_type', job.x_employment_type),
            'role_status': self._rn_format_value('x_role_status', job.x_role_status),
            'sub_status': job.x_sub_status and self._rn_format_value('x_sub_status', job.x_sub_status) or '',
            'positions': job.no_of_recruitment,
            'experience': experience,
            'commercial': commercial,
            'locations': ', '.join(job.x_location_ids.mapped('name')),
            'manager': job.user_id.name or '',
            'recruiters': ', '.join(job.x_recruiter_ids.mapped('name')),
            'candidates': len(applicants),
            'received_on': self._rn_date(job.x_role_received_date),
            'created_by': job.create_uid.name or '',
            'created_on': self._rn_local_date(job.create_date),
        }

    def _rn_notify(self, event, changes=None):
        if not self._rn_enabled('role'):
            return
        for job in self:
            job._rn_send('recruitment_pipeline_report.mail_template_rp_role',
                         job._rn_partners('role'),
                         {'rn_event': event, 'rn_changes': changes or []})

    @api.model_create_multi
    def create(self, vals_list):
        jobs = super().create(vals_list)
        jobs._rn_notify('created')
        return jobs

    def _message_track(self, fields_iter, initial_values_dict):
        """Mail whatever the audit log just recorded about a role. A change
        of Role Status to Closed is sent as its own Role Closed email."""
        tracking = super()._message_track(fields_iter, initial_values_dict)
        for job in self:
            changes = tracking.get(job.id, (None, None))[0]
            if not changes:
                continue
            initial = initial_values_dict[job.id]
            closed = 'x_role_status' in changes and job.x_role_status == 'closed'                 and initial.get('x_role_status') != 'closed'
            job._rn_notify('closed' if closed else 'updated',
                           job._rn_format_changes(changes, initial))
        return tracking

    def unlink(self):
        if len(self) == 1:
            subject = _('Role deleted: %s', self.display_name)
        else:
            subject = _('%(count)s roles deleted: %(names)s',
                        count=len(self), names=', '.join(self[:3].mapped('name')))
        self._rn_send_deleted('recruitment_pipeline_report.mail_template_rp_role', subject)
        return super().unlink()
