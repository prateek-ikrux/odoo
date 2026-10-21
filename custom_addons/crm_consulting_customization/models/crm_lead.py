# -*- coding: utf-8 -*-
import base64
import logging
from collections import Counter
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date

from .crm_stage_report_xlsx import build_stage_report_xlsx

_logger = logging.getLogger(__name__)

# System parameters holding which reminder days are switched on, comma
# separated, and the fallback when a parameter has never been set. An empty
# parameter is not the same as a missing one: it means the Admin cleared
# every chip, and nothing is sent.
ACTIVITY_REMINDER_DAYS_PARAM = 'crm_consulting.activity_reminder_days'
DEFAULT_REMINDER_DAYS = {
    ACTIVITY_REMINDER_DAYS_PARAM: '3,1',
}

# The weekly stuck-in-stage report: whether it is on, the weekday it goes out
# on at midnight (0 is Monday, as in Python), the days in one stage that make
# a client stuck, and the timezone that midnight is in - the one of whoever
# last saved the settings, so it is their weekday and their midnight.
STAGE_REPORT_PARAM = 'crm_consulting.stage_reminders'
STAGE_REPORT_WEEKDAY_PARAM = 'crm_consulting.stage_report_weekday'
STAGE_REPORT_MIN_DAYS_PARAM = 'crm_consulting.stage_report_min_days'
STAGE_REPORT_TZ_PARAM = 'crm_consulting.stage_report_tz'
DEFAULT_STAGE_REPORT_WEEKDAY = 0
DEFAULT_STAGE_REPORT_MIN_DAYS = 6

# The milestone flags, paired with the field that records when each was
# raised. Kept in one place so create() and write() stay in step with the
# field definitions instead of repeating the pairing.
MILESTONE_DATE_FIELDS = {
    'milestone_requirement_received': 'milestone_requirement_received_date',
    'milestone_delivery_started': 'milestone_delivery_started_date',
    'milestone_agreement_signed': 'milestone_agreement_signed_date',
}

# The numbers the opportunity form requires, with the label the form shows
# and the condition under which it shows them. The web client never enforces
# required on a number - 0 always passes as filled in - so _check_required_numbers
# holds the rule on the server instead.
#
# None is required today: Open Positions, Roles Open, Commercial Agreement and
# Project Duration are all optional, since a deal is often in the pipeline
# before the requirement or the commercials are known. Making one mandatory
# again is a line here plus required on the form field, for example:
#     'project_duration': ('Project Duration', lambda lead: lead.engagement_type != 'fte'),
REQUIRED_NUMBERS = {}

# The opportunity's own contact fields, each paired with the detail of the
# primary POC - the first in the POC list - that it holds a copy of.
PRIMARY_POC_FIELDS = {
    'contact_name': 'name',
    'function': 'designation',
    'phone': 'phone',
    'email_from': 'email',
    'poc1_location': 'location',
    'poc1_linkedin': 'linkedin',
}


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # -------------------------------------------------------------------
    # Ownership
    # -------------------------------------------------------------------
    # BDA is one idea with one field on the form: bda_ids, the people working
    # the account. Odoo's own Salesperson is not a second idea alongside it -
    # it is the single answer CRM needs internally, kept as one of the BDAs by
    # _sync_owner_from_bda below, and off the form entirely.
    bda_ids = fields.Many2many(
        'res.users',
        'crm_lead_bda_user_rel', 'lead_id', 'user_id',
        string='BDA',
        required=True,
        tracking=True,
        default=lambda self: self.env.user,
        domain=lambda self: self._bda_domain(),
        help='Everyone working this opportunity. A BDA sees an opportunity if '
             'they appear here.',
    )

    # The one BDA that CRM's own machinery needs a single answer for: who an
    # activity is assigned to, whose pipeline an opportunity counts in, whose
    # avatar shows on the kanban card. It is not a second concept and it is not
    # on the form - it follows the BDA list, and the list is what people edit.
    user_id = fields.Many2one(string='Primary BDA')

    # The opportunity's own title carries the client's name; the customer
    # link is off every view. It keeps a label of its own so the two are not
    # confused in an export, a filter or the import field list, and so
    # opportunities that already point at a company keep that link.
    name = fields.Char(string='Client Name')
    partner_id = fields.Many2one(string='Client Company')

    # Client Type and Industry / Domain belong to the opportunity. They are
    # entered here and held here; nothing reads them off the client record, so
    # classifying a deal never means leaving CRM. Ordinary stored columns,
    # which is what the pivot groups by.
    #
    # Client Type is mandatory on the form rather than on the field, the same
    # way Client Name is. crm.lead also backs leads raised by the incoming-mail
    # alias and the website form, neither of which can answer it, and a
    # requirement on the field would reject those outright. Everything a
    # person creates goes through a form, which is where the rule has to hold.
    # Industry / Domain is the one classification left optional.
    #
    # Both pick from a master list kept under CRM > Configuration (see
    # crm_classification.py), so a report grouped by either one still has a
    # fixed, countable set of buckets, but the Sales Manager owns the list.
    # The names predate the lists, when both were selections, and are kept so
    # import sheets and saved filters keep working.
    client_type = fields.Many2one(
        'crm.client.type',
        string='Client Type',
        index=True,
        tracking=True,
        ondelete='restrict',
    )

    industry_domain = fields.Many2one(
        'crm.industry.domain',
        string='Industry / Domain',
        index=True,
        tracking=True,
        ondelete='restrict',
    )

    client_status = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('hold', 'Hold'),
        ],
        string='Client Status',
        required=True,
        default='active',
        tracking=True,
    )

    # When the engagement starts and ends. Both optional and left empty until
    # someone knows them. They replace the Initial Outreach Date, which was
    # only ever pre-filled with the day the opportunity was created, and take
    # CRM's Expected Closing off the form (19.0.1.27.0) - that one stays in
    # the model, read by CRM's own forecast, but nothing here sets it.
    start_date = fields.Date('Start Date', tracking=True)
    end_date = fields.Date('End Date', tracking=True)

    # -------------------------------------------------------------------
    # Commercials
    # -------------------------------------------------------------------
    engagement_type = fields.Selection(
        selection=[
            ('fte', 'FTE'),
            ('consulting', 'Consulting'),
            ('fte_consulting', 'FTE/Consulting'),
        ],
        string='Engagement Type',
        required=True,
        default='fte',
        tracking=True,
    )

    # Every engagement agrees a Commercial Agreement; only the unit differs.
    # FTE is struck as a percentage and Consulting in rupee lakhs per month,
    # so for those two the basis follows from the type and is not the user's
    # to pick. A blended FTE/Consulting engagement can be struck either way,
    # so there - and only there - the field is theirs to set.
    commercial_basis = fields.Selection(
        selection=[
            ('percentage', 'Percentage'),
            ('lpm', 'Lakhs per Month'),
        ],
        string='Commercial Basis',
        compute='_compute_commercial_basis',
        store=True,
        readonly=False,
        tracking=True,
    )

    commercial_agreement_pct = fields.Float(
        'Commercial Agreement',
        digits=(5, 4),
        tracking=True,
        help='Agreed commercial as a percentage. Stored as a fraction - 8% is '
             'held as 0.08 - which is what the percentage widget reads and writes.',
    )

    # Float and not Monetary. The unit is lakhs per month, which is not a
    # currency: a Monetary field renders the company's symbol in front of the
    # figure, so 2.5 lakhs per month read as a rupee amount of 2.50. The unit
    # is written after the figure on the form instead, the way any other unit
    # is. Float with explicit digits keeps the same numeric column Monetary
    # used, so nothing already stored has to move.
    bill_rate_lpm = fields.Float(
        'Bill Rate',
        digits=(16, 2),
        tracking=True,
        help='Agreed commercial in lakhs per month. A count of lakhs, not a '
             'rupee figure - do not sum it against one.',
    )

    # Two different counts, deliberately kept apart. Open Positions is the
    # number of vacancies; Roles Open is how many distinct roles those
    # vacancies span. Ten openings across three roles is 10 and 3.
    open_positions = fields.Integer(
        'Open Positions',
        tracking=True,
        help='Total number of vacancies open on this engagement.',
    )

    roles_open = fields.Integer(
        'Roles Open',
        tracking=True,
        help='How many distinct roles those vacancies span - three vacancies '
             'for one role is 3 open positions and 1 role open.',
    )

    project_duration = fields.Integer(
        'Project Duration',
        tracking=True,
        help='Length of the engagement in months. Not applicable to a pure FTE '
             'engagement.',
    )

    # -------------------------------------------------------------------
    # Engagement milestones
    # -------------------------------------------------------------------
    # Flags, not stages. Nothing here is driven by stage_id and nothing here
    # drives it; each is raised and cleared by hand, and each stores the day
    # it was raised so cycle times can be measured.
    milestone_requirement_received = fields.Boolean(
        'Requirement Received', default=False, tracking=True)
    milestone_requirement_received_date = fields.Date(
        'Requirement Received On', readonly=True)

    milestone_delivery_started = fields.Boolean(
        'Delivery Started', default=False, tracking=True)
    milestone_delivery_started_date = fields.Date(
        'Delivery Started On', readonly=True)

    milestone_agreement_signed = fields.Boolean(
        'Agreement Signed', default=False, tracking=True)
    milestone_agreement_signed_date = fields.Date(
        'Agreement Signed On', readonly=True)

    # -------------------------------------------------------------------
    # POC contacts
    # -------------------------------------------------------------------
    # Every POC is a row in one list (crm.lead.poc), as many as the
    # opportunity needs, in the order dragged on the form. The first is the
    # primary contact. Each belongs to the opportunity that found them rather
    # than being shared across opportunities.
    #
    # The opportunity's own contact fields - CRM's name, job position, email
    # and phone, plus a location and a LinkedIn profile - hold a copy of the
    # primary POC. They are off the form, but Send Email and Send SMS, the
    # pipeline card, the lists and the emails this module sends all read
    # them, so they follow the first row of the list wherever it changes.
    #
    # What is not kept is CRM's syncing of them with the customer. Here the
    # Client Name is the client company and the POC a person at it, two
    # different parties, so neither is filled in from the other.
    #
    # None of them is copied with the opportunity: the POC list is, and a
    # duplicate takes its copy from that, rather than having the copied
    # fields read as a new POC to add.
    contact_name = fields.Char(string='POC Name', copy=False)
    function = fields.Char(string='Designation', copy=False)
    phone = fields.Char(string='Phone Number', copy=False)
    email_from = fields.Char(copy=False)

    poc1_location = fields.Char(
        'POC Location', compute='_compute_primary_poc_extras', readonly=False, store=True,
        copy=False)
    poc1_linkedin = fields.Char(
        'POC LinkedIn', compute='_compute_primary_poc_extras', readonly=False, store=True,
        copy=False)

    # Copied with the opportunity.
    poc_ids = fields.One2many(
        'crm.lead.poc', 'lead_id', string='POCs', copy=True)

    def _get_primary_poc(self):
        """The first POC in the list. Sorted by the position alone, as the
        sort is stable and an unsaved row has no id to break a tie with."""
        self.ensure_one()
        return self.poc_ids.sorted('sequence')[:1]

    def _copy_primary_poc(self, fnames):
        for lead in self:
            primary = lead._get_primary_poc()
            for fname in fnames:
                lead[fname] = primary[PRIMARY_POC_FIELDS[fname]]

    # CRM's own computes for these fill them in from the customer; each is
    # replaced by a copy of the primary POC.

    @api.depends('poc_ids.sequence', 'poc_ids.name')
    def _compute_contact_name(self):
        self._copy_primary_poc(['contact_name'])

    @api.depends('poc_ids.sequence', 'poc_ids.designation')
    def _compute_function(self):
        self._copy_primary_poc(['function'])

    @api.depends('poc_ids.sequence', 'poc_ids.email')
    def _compute_email_from(self):
        self._copy_primary_poc(['email_from'])

    @api.depends('poc_ids.sequence', 'poc_ids.phone')
    def _compute_phone(self):
        self._copy_primary_poc(['phone'])

    @api.depends('poc_ids.sequence', 'poc_ids.location', 'poc_ids.linkedin')
    def _compute_primary_poc_extras(self):
        self._copy_primary_poc(['poc1_location', 'poc1_linkedin'])

    def _inverse_email_from(self):
        """The POC's email stays with the POC; the client company keeps its
        own."""

    def _inverse_phone(self):
        """The POC's phone stays with the POC; the client company keeps its
        own."""

    @staticmethod
    def _primary_poc_values(vals):
        """The POC details in vals written straight onto the opportunity, as
        POC values."""
        return {poc_f: vals[lead_f] for lead_f, poc_f in PRIMARY_POC_FIELDS.items()
                if lead_f in vals}

    def _put_primary_poc_in_list(self, values, replace):
        """Contact details written straight onto the opportunity - an import's
        POC columns, a lead raised from an incoming email - go into the POC
        list, so they show on the form.

        A new opportunity gets them as a new first row, ahead of any other
        POC it came with. An edit to an existing one changes its first row,
        or adds one if the list is empty.
        """
        for lead in self:
            primary = lead._get_primary_poc() if replace else lead.poc_ids.browse()
            if primary:
                primary.write(values)
            elif any(values.values()):
                first = min(lead.poc_ids.mapped('sequence') or [11])
                self.env['crm.lead.poc'].create(dict(values, lead_id=lead.id, sequence=first - 1))

    @api.depends('email_from', 'partner_id')
    def _compute_partner_email_update(self):
        # Drives CRM's "this will update the customer" hint, which no longer
        # applies now that nothing is written back.
        self.partner_email_update = False

    @api.depends('phone', 'partner_id')
    def _compute_partner_phone_update(self):
        self.partner_phone_update = False

    @api.model
    def _bda_domain(self):
        """Who can be picked as a BDA: internal users with Sales access.

        Anyone else could be put on an opportunity they cannot open, and be
        mailed links to it. Only the picker is limited, not the field: someone
        whose Sales access is later taken away stays on the opportunities they
        worked, rather than every later save of those being refused.
        """
        return [
            ('share', '=', False),
            ('all_group_ids', 'in', self.env.ref('sales_team.group_sale_salesman').ids),
        ]

    # -------------------------------------------------------------------
    # Computes
    # -------------------------------------------------------------------
    @api.depends('engagement_type')
    def _compute_commercial_basis(self):
        for lead in self:
            if lead.engagement_type == 'fte':
                lead.commercial_basis = 'percentage'
            elif lead.engagement_type == 'consulting':
                lead.commercial_basis = 'lpm'
            else:
                # Blended: the deal could have been struck either way, so keep
                # whatever was chosen and only fall back when nothing was.
                lead.commercial_basis = lead.commercial_basis or 'percentage'

    # -------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------
    @api.constrains('bda_ids', 'type')
    def _check_bda_ids(self):
        """required=True on a many2many is enforced by the web client but not
        by the database, so an import or an RPC call could still leave an
        opportunity with nobody on it. Leads are left alone - they are created
        unattended, from incoming mail among other things, long before anyone
        has been assigned.

        Read with active_test off. A many2many to res.users hides archived
        users by default, so an opportunity whose only BDA has since left the
        company would otherwise read as having none - and every later write to
        it would be refused for a field nobody had touched. The same applies
        to anything running as OdooBot, which is itself an archived user.
        """
        for lead in self.with_context(active_test=False):
            if lead.type == 'opportunity' and not lead.bda_ids:
                raise ValidationError(
                    _('An opportunity needs at least one BDA assigned.'))

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for lead in self:
            if lead.start_date and lead.end_date and lead.end_date < lead.start_date:
                raise ValidationError(_('The End Date cannot be before the Start Date.'))

    def _check_required_numbers(self, fnames):
        """Refuse a zero in a number the form marks as required.

        Only the numbers being written are checked, and those whose turn to
        show has just come - a change of engagement type or commercial basis
        can bring one onto the form (today, Project Duration when a deal stops
        being pure FTE). A new record from the form sends every field on it,
        so it is checked in full; a lead from the mail alias sends none of
        these and a kanban drag sends only the stage, so neither is refused
        for a number nobody was asked for.
        """
        fnames = set(fnames)
        if fnames & {'engagement_type', 'commercial_basis'}:
            fnames |= set(REQUIRED_NUMBERS)
        checked = [fname for fname in REQUIRED_NUMBERS if fname in fnames]
        if not checked:
            return
        for lead in self:
            missing = []
            for fname in checked:
                label, applies = REQUIRED_NUMBERS[fname]
                if applies(lead) and lead[fname] <= 0 and label not in missing:
                    missing.append(label)
            if missing:
                raise ValidationError(_(
                    'These fields are mandatory and must be greater than zero: %s',
                    ', '.join(missing)))

    # -------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        # An opportunity created with a salesperson but no BDA list - by an
        # import, or by CRM's own lead conversion - names that person as its
        # only BDA, rather than falling through to the field default and
        # crediting whoever happened to run the job.
        vals_list = [
            dict(vals, bda_ids=[fields.Command.set([vals['user_id']])])
            if vals.get('user_id') and not vals.get('bda_ids')
            else vals
            for vals in vals_list
        ]
        leads = super().create(vals_list)
        for lead, vals in zip(leads, vals_list):
            lead._check_required_numbers(vals)
            if values := self._primary_poc_values(vals):
                lead._put_primary_poc_in_list(values, replace=False)
        leads._sync_owner_from_bda()
        raised = {
            flag: True
            for flag in MILESTONE_DATE_FIELDS
            if any(vals.get(flag) for vals in vals_list)
        }
        if raised:
            leads._stamp_milestone_dates(raised)
        leads._send_change_notification('created')
        return leads

    def write(self, vals):
        res = super().write(vals)
        self._check_required_numbers(vals)
        if values := self._primary_poc_values(vals):
            self._put_primary_poc_in_list(values, replace=True)
        # The BDA list is what people edit, so it wins when both are written.
        if 'bda_ids' in vals:
            self._sync_owner_from_bda()
        elif 'user_id' in vals:
            self._sync_bda_from_owner()
        self._stamp_milestone_dates(vals)
        return res

    # Two directions of the same rule: the primary BDA is always one of the
    # BDAs. Ownership is read by the record rule and by every report grouped
    # by BDA, and both are simpler for there being one list to consult.
    #
    # active_test is off in both for the same reason as in _check_bda_ids: an
    # archived colleague is still on the record, and a read that hides them
    # would have these two rewriting each other every time.

    def _sync_owner_from_bda(self):
        """Point the primary BDA at someone who is actually on the list.

        Only when the current one has dropped off it - so taking a colleague
        off an opportunity does not silently hand it to somebody else, and
        re-saving never shuffles who owns what.
        """
        for lead in self.with_context(active_test=False):
            if lead.bda_ids and lead.user_id not in lead.bda_ids:
                lead.user_id = lead.bda_ids[0]

    def _sync_bda_from_owner(self):
        """Add a newly named primary BDA to the list, for the paths that still
        set the salesperson directly - lead conversion, imports, assignment
        rules - none of which know about the list."""
        for lead in self.with_context(active_test=False):
            if lead.user_id and lead.user_id not in lead.bda_ids:
                lead.bda_ids = [fields.Command.link(lead.user_id.id)]

    def _stamp_milestone_dates(self, vals):
        """Record the day a milestone was raised, and clear it when lowered.

        The date is stamped only on the move, so re-saving an opportunity
        whose milestone was already raised does not shift the date and lose
        the cycle time.
        """
        for flag_field, date_field in MILESTONE_DATE_FIELDS.items():
            if flag_field not in vals:
                continue
            for lead in self:
                if lead[flag_field] and not lead[date_field]:
                    lead[date_field] = fields.Date.context_today(lead)
                elif not lead[flag_field] and lead[date_field]:
                    lead[date_field] = False

    # -------------------------------------------------------------------
    # Email notifications
    # -------------------------------------------------------------------
    # Change notifications and activity reminders follow one hierarchy of
    # three levels, read from what is already set up rather than stored:
    #
    #   Leadership  - the people picked under Leadership in CRM settings
    #   Managers    - the leaders of active sales teams
    #   BDAs        - everyone else, filed under the leader of their team
    #
    # Someone on two levels counts at the higher. The stuck-in-stage report is
    # a weekly summary rather than news about one person's work, and keeps a
    # list of its own. Only opportunities: leads raised by the mail alias or
    # the website form would otherwise mail people about records nobody has
    # looked at yet.

    @api.model
    def _get_reminder_days(self, param):
        """Days a reminder kind is switched on for, most distant first.

        get_param falls back to the default for an empty value too, which
        would bring back reminders cleared on purpose in the settings, so only
        a parameter that does not exist at all takes the default.
        """
        raw = self.env['ir.config_parameter'].sudo()._get_param(param)
        if raw is None:
            raw = DEFAULT_REMINDER_DAYS.get(param, '')
        days = set()
        for chunk in (raw or '').split(','):
            chunk = chunk.strip()
            if chunk.isdigit() and int(chunk) > 0:
                days.add(int(chunk))
        return sorted(days, reverse=True)

    @api.model
    def _notify_enabled(self, param):
        return bool(self.env['ir.config_parameter'].sudo().get_param(param))

    @api.model
    def _mail_partners(self, users):
        """The partners behind users who can actually be mailed."""
        return users.filtered(lambda u: u.active and u.email).partner_id

    @api.model
    def _mail_email_to(self, partners):
        """Everyone on one To line, so a notification goes out as a single
        email they all share. Odoo sends a separate copy to each partner in
        ``recipient_ids``; ``email_to`` goes out once, to all of it."""
        return ', '.join(partners.mapped('email_formatted'))

    @api.model
    def _mail_email_values(self, partners):
        """Send-mail values addressing a template's email to ``partners``
        alone, on one shared To line.

        ``recipient_ids`` is emptied as well: left alone, the template falls back
        on the record's own default recipients - a lead's customer, a
        candidate - and would mail them the internal notification too.
        """
        return {'email_to': self._mail_email_to(partners), 'recipient_ids': []}

    def _get_bda_users(self):
        # Archived BDAs are still on the record; read them, the mailer drops them.
        return self.sudo().with_context(active_test=False).bda_ids

    @api.model
    def _get_leadership(self):
        return self.env.company.sudo().crm_leadership_ids

    @api.model
    def _get_team_leaders(self, users):
        """The leaders of the sales teams these users are members of now.

        Read with archived records showing, as BDAs are, so a past membership
        or an archived team is dropped here rather than mailed.
        """
        members = users.sudo().with_context(active_test=False).crm_team_member_ids
        return members.filtered('active').crm_team_id.filtered('active').user_id

    @api.model
    def _get_hierarchy_level(self, user, leadership):
        """2 for leadership, 1 for a sales team leader, 0 for everyone else."""
        if user in leadership:
            return 2
        if self.env['crm.team'].sudo().search_count([('user_id', '=', user.id)], limit=1):
            return 1
        return 0

    @api.model
    def _get_users_above(self, user, team_leader=True, leadership=True):
        """Everyone above user in the hierarchy - the leader of their sales
        team and leadership, either of which can be left out - and never user
        themselves. Only a level higher than user's own counts, so a manager
        has leadership above them and leadership has nobody."""
        all_leadership = self._get_leadership()
        level = self._get_hierarchy_level(user, all_leadership)
        above = self.env['res.users']
        if team_leader and level < 1:
            above |= self._get_team_leaders(user)
        if leadership and level < 2:
            above |= all_leadership
        return above - user

    def _get_form_url(self):
        """Straight into the opportunity, from the Pipeline."""
        self.ensure_one()
        return f'{self.get_base_url()}/odoo/action-crm.crm_lead_action_pipeline/{self.id}'

    def _changed_by(self):
        # Crons run as the superuser; naming OdooBot would only puzzle.
        return _('Automatic update') if self.env.user._is_superuser() else self.env.user.name

    @staticmethod
    def _short_date(env, value):
        return format_date(env, value, date_format='d MMM y') if value else ''

    @staticmethod
    def _long_date(env, value):
        return format_date(env, value, date_format='EEEE, d MMMM y') if value else ''

    def _selection_label(self, fname):
        return dict(self._fields[fname]._description_selection(self.env)).get(self[fname], '')

    def _get_mail_details(self):
        """The opportunity's key facts, formatted for every CRM email."""
        self.ensure_one()
        lead = self.sudo()
        if lead.commercial_basis == 'lpm':
            commercial = _('%s lakhs / month', f'{lead.bill_rate_lpm:g}') if lead.bill_rate_lpm else ''
        else:
            commercial = f'{lead.commercial_agreement_pct * 100:g}%' if lead.commercial_agreement_pct else ''
        next_activity = lead.activity_ids.sorted(lambda a: (a.date_deadline, a.id))[:1]
        created_on = fields.Datetime.context_timestamp(
            lead.with_user(lead.create_uid), lead.create_date) if lead.create_date else False
        if not lead.active:
            status = _('Lost')
        elif lead.stage_id.is_won:
            status = _('Won')
        else:
            status = _('Open')
        return {
            'name': lead.name or '',
            'client_type': lead.client_type.name or '',
            'industry': lead.industry_domain.name or '',
            'engagement_type': lead._selection_label('engagement_type'),
            'commercial': commercial,
            'client_status': lead._selection_label('client_status'),
            'stage': lead.stage_id.name or '',
            'bdas': ', '.join(lead._get_bda_users().mapped('name')),
            'poc': ' - '.join(p for p in (lead.contact_name, lead.function) if p),
            'poc_contact': ' | '.join(p for p in (lead.email_from, lead.phone) if p),
            'start_date': self._short_date(self.env, lead.start_date),
            'end_date': self._short_date(self.env, lead.end_date),
            'status': status,
            'lost_reason': (lead.lost_reason_id.name or '') if not lead.active else '',
            'created_by': lead.create_uid.name or '',
            'created_on': self._short_date(self.env, created_on),
            'next_activity': ' - '.join(p for p in (
                next_activity.activity_type_id.name,
                next_activity.summary,
                self._short_date(self.env, next_activity.date_deadline),
            ) if p) if next_activity else '',
        }

    def _send_lead_mail(self, template_xmlid, partners, values):
        """Queue one email for this opportunity. Never raises: an email that
        cannot be built is logged and dropped, and the change it reports on
        goes through regardless."""
        self.ensure_one()
        if not partners:
            return False
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            _logger.warning("CRM notification: mail template %s is missing.", template_xmlid)
            return False
        try:
            with self.env.cr.savepoint():
                template.sudo().with_context(
                    crm_url=self._get_form_url(),
                    crm_details=self._get_mail_details(),
                    crm_changed_by=self._changed_by(),
                    **values,
                ).send_mail(
                    self.id,
                    email_values=self._mail_email_values(partners),
                    force_send=False,
                )
            return True
        except Exception:
            _logger.exception("CRM notification %s failed for opportunity %s.",
                              template_xmlid, self.id)
            return False

    # ── Change notifications ──────────────────────────────────────
    def _get_change_partners(self):
        """Everyone above whoever made the change, or nobody while change
        notifications are off.

        A change made by a scheduled job has nobody behind it to rank, so it
        goes to the whole of these opportunities' hierarchy instead: their
        BDAs, the BDAs' team leaders, and leadership.
        """
        if not self._notify_enabled('crm_consulting.change_notify'):
            return self.env['res.partner']
        actor = self.env.user
        if actor._is_superuser():
            bdas = self._get_bda_users()
            users = bdas | self._get_team_leaders(bdas) | self._get_leadership()
        else:
            users = self._get_users_above(actor)
        return self._mail_partners(users)

    def _send_change_notification(self, event, changes=None):
        for lead in self.filtered(lambda l: l.type == 'opportunity'):
            lead._send_lead_mail(
                'crm_consulting_customization.mail_template_crm_lead_created' if event == 'created'
                else 'crm_consulting_customization.mail_template_crm_lead_updated',
                lead._get_change_partners(),
                {'crm_changes': changes or []},
            )

    def _message_track(self, fields_iter, initial_values_dict):
        """Mail whatever the audit log just recorded.

        This is where mail.thread turns tracked-field changes into the
        chatter's log entry, once per record per transaction, so hooking in
        here mails exactly what the log shows - from the form, a kanban drag,
        an import or a cron alike.
        """
        tracking = super()._message_track(fields_iter, initial_values_dict)
        for lead in self:
            changes = tracking.get(lead.id, (None, None))[0]
            if changes:
                lead._send_change_notification(
                    'updated', lead._format_changes(changes, initial_values_dict[lead.id]))
        return tracking

    def _format_changes(self, changes, initial_values):
        """Old and new value of each changed field, as display text, in the
        order the fields are declared."""
        self.ensure_one()
        return [
            {
                'field': self._fields[fname]._description_string(self.env),
                'old': self._format_tracked_value(fname, initial_values.get(fname)),
                'new': self._format_tracked_value(fname, self[fname]),
            }
            for fname in self._fields if fname in changes
        ]

    def _format_tracked_value(self, fname, value):
        field = self._fields[fname]
        empty = '—'
        if field.type == 'boolean':
            return _('Yes') if value else _('No')
        if field.type in ('integer', 'float', 'monetary'):
            return f'{value or 0:g}'
        if value is None or value is False or value == '':
            return empty
        if field.type == 'selection':
            return dict(field._description_selection(self.env)).get(value, value)
        if field.type in ('many2one', 'many2many', 'one2many'):
            return ', '.join(value.sudo().mapped('display_name')) or empty
        if field.type == 'date':
            return self._short_date(self.env, value)
        if field.type == 'datetime':
            return fields.Datetime.to_string(fields.Datetime.context_timestamp(self, value))[:16]
        return str(value)

    # ── Deletion ──────────────────────────────────────────────────
    def unlink(self):
        self._send_deletion_notification()
        return super().unlink()

    def _send_deletion_notification(self):
        """One email listing every opportunity about to be deleted.

        Built before the delete, while the records can still be read, and not
        linked to them: mail.thread removes every message tied to a record it
        deletes, which would take a queued email with it. If the delete itself
        fails, the transaction rolls the email back too.
        """
        leads = self.filtered(lambda l: l.type == 'opportunity')
        if not leads:
            return
        partners = leads._get_change_partners()
        template = self.env.ref('crm_consulting_customization.mail_template_crm_lead_deleted',
                                raise_if_not_found=False)
        if not partners or not template:
            return
        try:
            with self.env.cr.savepoint():
                lead = leads[0]
                if len(leads) == 1:
                    subject = _('Opportunity deleted: %s', lead.name)
                else:
                    subject = _('%(count)s opportunities deleted: %(names)s%(more)s',
                                count=len(leads),
                                names=', '.join(leads[:3].mapped('name')),
                                more=_(' and more') if len(leads) > 3 else '')
                template = template.sudo().with_context(
                    crm_subject=subject,
                    crm_deleted=[rec._get_mail_details() for rec in leads],
                    crm_changed_by=self._changed_by(),
                )
                self.env['mail.mail'].sudo().create({
                    'subject': template._render_field('subject', lead.ids)[lead.id],
                    'body_html': template._render_field('body_html', lead.ids)[lead.id],
                    'email_to': self._mail_email_to(partners),
                    'auto_delete': True,
                })
        except Exception:
            # A notification must never block the deletion it reports on.
            _logger.exception("CRM deletion notification failed for %s.", leads.ids)

    # ── Stuck-in-stage report ─────────────────────────────────────
    # One email a week, at midnight on the weekday picked in CRM settings,
    # carrying an Excel list of every active client whose opportunity has sat
    # in one stage for at least the days picked there. How long it has sat is
    # CRM's own date_last_stage_update, which CRM resets on every stage change.

    @api.model
    def _stage_report_settings(self):
        """(weekday, min_days, tz) as set in CRM settings."""
        params = self.env['ir.config_parameter'].sudo()
        weekday = params.get_param(STAGE_REPORT_WEEKDAY_PARAM) or ''
        min_days = params.get_param(STAGE_REPORT_MIN_DAYS_PARAM) or ''
        try:
            tz = pytz.timezone(params.get_param(STAGE_REPORT_TZ_PARAM) or 'UTC')
        except pytz.UnknownTimeZoneError:
            tz = pytz.utc
        weekday = int(weekday) if weekday.isdigit() and int(weekday) < 7 \
            else DEFAULT_STAGE_REPORT_WEEKDAY
        min_days = int(min_days) if min_days.isdigit() and int(min_days) > 0 \
            else DEFAULT_STAGE_REPORT_MIN_DAYS
        return weekday, min_days, tz

    @api.model
    def _cron_send_stage_report(self):
        """The weekly run. Sends nothing while the report is switched off."""
        if not self._notify_enabled(STAGE_REPORT_PARAM):
            return True
        self._send_stage_report()
        return True

    @api.model
    def _get_stage_report_rows(self, report_date, min_days, tz):
        """Active clients' opportunities in a stage that is in the report,
        in that stage for min_days or more as of report_date - longest first.

        Days are counted between calendar days in the report's timezone, so
        an opportunity that moved last Monday is 7 days in stage on the
        following Monday, whatever the hour either happened at.
        """
        # In stage since report_date - min_days or earlier: moved before the
        # local midnight that starts the day after that.
        cutoff = tz.localize(datetime.combine(
            report_date - timedelta(days=min_days - 1), time.min,
        )).astimezone(pytz.utc).replace(tzinfo=None)
        leads = self.sudo().search([
            ('type', '=', 'opportunity'),
            ('client_status', '=', 'active'),
            ('stage_id.stage_reminders', '=', True),
            '|', ('date_last_stage_update', '<', cutoff),
                 '&', ('date_last_stage_update', '=', False), ('create_date', '<', cutoff),
        ])
        rows = []
        for lead in leads:
            moved = lead.date_last_stage_update or lead.create_date
            entered = pytz.utc.localize(moved).astimezone(tz).date()
            days = (report_date - entered).days
            details = lead._get_mail_details()
            rows.append({
                'client': lead.name or '',
                'stage': lead.stage_id.name or '',
                'since': self._short_date(self.env, entered),
                'days': days,
                'bdas': details['bdas'],
                'client_type': details['client_type'],
                'industry': details['industry'],
                'engagement_type': details['engagement_type'],
                'poc': lead.contact_name or '',
                'poc_phone': lead.phone or '',
                'poc_email': lead.email_from or '',
                'next_activity': details['next_activity'],
                'start_date': details['start_date'],
                'end_date': details['end_date'],
                'url': lead._get_form_url(),
            })
        rows.sort(key=lambda r: (-r['days'], r['client'].lower()))
        return rows

    @api.model
    def _send_stage_report(self, report_date=None):
        """Build the report as of report_date - today in the report's
        timezone by default - and email it to the people picked in CRM
        settings. Returns how many people it went to.

        Sent even when nobody is stuck, so a quiet week still arrives and
        says so, rather than leaving the list wondering whether it ran.
        """
        _weekday, min_days, tz = self._stage_report_settings()
        partners = self._mail_partners(self.env.company.sudo().crm_stage_reminder_recipient_ids)
        template = self.env.ref('crm_consulting_customization.mail_template_crm_stage_report',
                                raise_if_not_found=False)
        if not partners or not template:
            if not template:
                _logger.warning("CRM stuck-in-stage report: mail template is missing.")
            return 0
        report_date = report_date or pytz.utc.localize(fields.Datetime.now()).astimezone(tz).date()
        rows = self._get_stage_report_rows(report_date, min_days, tz)
        as_of = self._long_date(self.env, report_date)
        plural = '' if len(rows) == 1 else 's'
        values = {
            'count': len(rows),
            'min_days': min_days,
            'as_of': as_of,
            'by_stage': sorted(Counter(r['stage'] for r in rows).items(), key=lambda kv: -kv[1]),
            'longest': rows[:5],
            'subject': _('Stuck-in-stage report: %(count)s client%(s)s, %(date)s',
                         count=len(rows), s=plural,
                         date=self._short_date(self.env, report_date)),
        }
        email_values = self._mail_email_values(partners)
        if rows:
            xlsx = build_stage_report_xlsx(
                rows,
                _('Stuck-in-Stage Report'),
                _('Active clients in the same stage for %(days)s days or more, as of '
                  '%(date)s - %(count)s client%(s)s',
                  days=min_days, date=as_of, count=len(rows), s=plural),
                min_days,
            )
            email_values['attachments'] = [(
                'Stuck_Clients_%s.xlsx' % report_date.strftime('%Y-%m-%d'),
                base64.b64encode(xlsx),
            )]
        template.sudo().with_context(crm_stage_report=values).send_mail(
            self.env.company.id, email_values=email_values, force_send=False)
        # Out now, not on the mail queue's next hourly run.
        self.env.ref('mail.ir_cron_mail_scheduler_action')._trigger()
        return len(partners)

    # ── Chatter mentions ──────────────────────────────────────────
    # Tagging a colleague with @ makes them a direct recipient of the
    # message. Odoo's own email for that is the bare message, which says
    # neither that they were tagged nor where. On an opportunity they get an
    # email of this module's instead, saying who tagged them on which
    # opportunity, with the message and a button into it - and the Inbox
    # notification Odoo gives them anyway, whatever their own preference.

    def _notify_get_recipients(self, message, msg_vals=False, **kwargs):
        """Take tagged colleagues off Odoo's email for the message - they get
        _notify_thread's own instead - and leave them its Inbox notification.

        Followers who were not tagged, people outside the company, and
        system messages such as assignment notices, keep to Odoo's own. Off
        unless switched on under CRM > Configuration > Settings.
        """
        recipients_data = super()._notify_get_recipients(message, msg_vals=msg_vals, **kwargs)
        if not self._notify_enabled('crm_consulting.mention_email'):
            return recipients_data
        msg_vals = msg_vals or {}
        msg_sudo = message.sudo()
        message_type = msg_vals['message_type'] if 'message_type' in msg_vals else msg_sudo.message_type
        if message_type != 'comment' or kwargs.get('notify_skip_followers'):
            return recipients_data
        pids = msg_vals['partner_ids'] if 'partner_ids' in msg_vals else msg_sudo.partner_ids.ids
        for rdata in recipients_data:
            if rdata['id'] in pids and rdata['type'] == 'user':
                rdata['notif'] = 'inbox'
                rdata['crm_tagged'] = True
        return recipients_data

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        recipients_data = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
        # A scheduled message is notified when it goes out; this runs again then.
        if self._is_notification_scheduled(kwargs.get('scheduled_date')):
            return recipients_data
        tagged = self.env['res.partner'].browse(
            r['id'] for r in recipients_data if r.get('crm_tagged') and r['email_normalized'])
        if tagged and len(self) == 1:
            self._send_tagged_mail(message, tagged)
        return recipients_data

    def _send_tagged_mail(self, message, partners):
        """Tell each tagged colleague who tagged them, on which opportunity,
        and what the message said."""
        msg = message.sudo()
        self._send_lead_mail(
            'crm_consulting_customization.mail_template_crm_tagged',
            partners,
            {'crm_tagged': {
                'by': msg.author_id.name or _('Someone'),
                'kind': _('an internal note') if msg.subtype_id.internal else _('a message'),
                'body': msg.body,
                'attachments': msg.attachment_ids.mapped('name'),
                'sent_on': self._long_date(self.env, fields.Datetime.context_timestamp(
                    self, msg.date).date()) if msg.date else '',
            }},
        )
