# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

# System parameters holding which reminder days are switched on, comma
# separated, and the fallback when a parameter has never been set. An empty
# parameter is not the same as a missing one: it means the Admin cleared
# every chip, and nothing is sent.
STAGE_REMINDER_DAYS_PARAM = 'crm_consulting.stage_reminder_days'
ACTIVITY_REMINDER_DAYS_PARAM = 'crm_consulting.activity_reminder_days'
DEFAULT_REMINDER_DAYS = {
    STAGE_REMINDER_DAYS_PARAM: '6,12,18,30',
    ACTIVITY_REMINDER_DAYS_PARAM: '3,1',
}

# The milestone flags, paired with the field that records when each was
# raised. Kept in one place so write() and the cycle-time computation stay in
# step with the field definitions instead of repeating the pairing.
MILESTONE_DATE_FIELDS = {
    'milestone_requirement_received': 'milestone_requirement_received_date',
    'milestone_delivery_started': 'milestone_delivery_started_date',
    'milestone_agreement_signed': 'milestone_agreement_signed_date',
}

# The fields a POC block 2-5 is made of. Named once so _compute_show_poc
# cannot fall behind the field definitions below.
POC_SUFFIXES = ('name', 'designation', 'phone', 'email', 'location', 'linkedin')

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
        domain="[('share', '=', False)]",
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

    initial_outreach_date = fields.Date(
        'Initial Outreach Date',
        # Optional, but pre-filled with the day the opportunity is created.
        default=fields.Date.context_today,
        tracking=True,
        help='The day first contact was made. Start of the cycle time measured '
             'against the date the agreement was signed.',
    )

    # Odoo already carries an "Expected Closing" date that its own forecast and
    # rotting logic read. Relabelled rather than duplicated, so the native
    # reporting keeps pointing at the field the business actually fills in.
    date_deadline = fields.Date(string='Expected Closure Date')

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
    # Stuck-in-stage reminders
    # -------------------------------------------------------------------
    # The days-in-stage mark of the last reminder sent. Zero means none yet;
    # a change of stage resets it, so each stage starts its own sequence.
    # How long the opportunity has been in its stage is CRM's own
    # date_last_stage_update, which CRM resets on every stage change.
    stage_reminder_sent_days = fields.Integer(
        'Stuck Reminder Sent At', readonly=True, copy=False,
        help='Days-in-stage mark of the last stuck-in-stage reminder sent for '
             'this opportunity. Reset whenever the stage changes.')

    # -------------------------------------------------------------------
    # POC contacts
    # -------------------------------------------------------------------
    # Five fixed blocks rather than a linked list: a POC belongs to the
    # opportunity that found them and is not meant to be reused across
    # opportunities. POC 1 is the primary contact and every field of it is
    # mandatory on the form; 2 to 5 are optional, but once a block is opened
    # the form asks for every field in it.
    #
    # POC 1 is not a new set of fields. An opportunity already carries the
    # name, job position, email and phone of the person being dealt with, and
    # that person is the primary POC - so POC 1 is those fields, relabelled,
    # with only the location and the LinkedIn profile genuinely new. Keeping
    # them means the POC still drives Send Email and Send SMS, and still shows
    # in CRM's own lists and reports.
    #
    # What is not kept is CRM's syncing of them with the customer. Here the
    # Client Name is the client company and the POC a person at it, two
    # different parties, so neither is filled in from the other - see the
    # "Client and POC kept apart" overrides below.
    contact_name = fields.Char(string='POC Name')
    function = fields.Char(string='Designation')
    phone = fields.Char(string='Phone Number')

    poc1_location = fields.Char('POC Location')
    poc1_linkedin = fields.Char('POC LinkedIn')

    poc2_name = fields.Char('POC 2 Name')
    poc2_designation = fields.Char('POC 2 Designation')
    poc2_phone = fields.Char('POC 2 Phone Number')
    poc2_email = fields.Char('POC 2 Email')
    poc2_location = fields.Char('POC 2 Location')
    poc2_linkedin = fields.Char('POC 2 LinkedIn')

    poc3_name = fields.Char('POC 3 Name')
    poc3_designation = fields.Char('POC 3 Designation')
    poc3_phone = fields.Char('POC 3 Phone Number')
    poc3_email = fields.Char('POC 3 Email')
    poc3_location = fields.Char('POC 3 Location')
    poc3_linkedin = fields.Char('POC 3 LinkedIn')

    poc4_name = fields.Char('POC 4 Name')
    poc4_designation = fields.Char('POC 4 Designation')
    poc4_phone = fields.Char('POC 4 Phone Number')
    poc4_email = fields.Char('POC 4 Email')
    poc4_location = fields.Char('POC 4 Location')
    poc4_linkedin = fields.Char('POC 4 LinkedIn')

    poc5_name = fields.Char('POC 5 Name')
    poc5_designation = fields.Char('POC 5 Designation')
    poc5_phone = fields.Char('POC 5 Phone Number')
    poc5_email = fields.Char('POC 5 Email')
    poc5_location = fields.Char('POC 5 Location')
    poc5_linkedin = fields.Char('POC 5 LinkedIn')

    # One POC is shown; each further one is asked for. Each flag reveals its
    # own block and, with it, the toggle that asks for the next - so the form
    # opens on POC 1 and walks out to five, never further. Odoo 19 has no
    # collapsible group in a form view, so the reveal is a field the group's
    # invisible condition reads.
    #
    # Computed and unstored on purpose: they add no columns, toggling one
    # writes nothing, and an opportunity that already has a POC 4 opens with
    # 2, 3 and 4 showing rather than hiding data behind a closed group.
    # One label each. The form calls all four "Add another POC", because that
    # is what the toggle under a block does; the fields themselves are named
    # apart so they stay distinguishable in an export, a filter or a log.
    show_poc2 = fields.Boolean(
        'Show POC 2', compute='_compute_show_poc', readonly=False, store=False)
    show_poc3 = fields.Boolean(
        'Show POC 3', compute='_compute_show_poc', readonly=False, store=False)
    show_poc4 = fields.Boolean(
        'Show POC 4', compute='_compute_show_poc', readonly=False, store=False)
    show_poc5 = fields.Boolean(
        'Show POC 5', compute='_compute_show_poc', readonly=False, store=False)

    # -------------------------------------------------------------------
    # Client and POC kept apart
    # -------------------------------------------------------------------
    # CRM treats the customer and the person dealt with as one party: picking
    # a customer copies its name, designation, email and phone into the
    # contact fields, and editing the contact's email or phone writes them
    # back onto the customer. Here the customer is the client company and
    # the contact fields are POC 1, so that copying put the company's details
    # in the POC and, the other way, overwrote the company's email and phone
    # with the POC's own.
    #
    # Each compute below keeps whatever the field already holds - typed in,
    # imported, or empty - which is the same thing CRM's own computes do
    # whenever the customer has nothing to copy, made unconditional.

    @api.depends('partner_id')
    def _compute_contact_name(self):
        """POC Name is the person's, typed in; never the client's name."""
        for lead in self:
            lead.contact_name = lead.contact_name

    @api.depends('partner_id')
    def _compute_function(self):
        """Designation is the POC's, never taken from the client record."""
        for lead in self:
            lead.function = lead.function

    @api.depends('partner_id.email')
    def _compute_email_from(self):
        """POC Email is the person's, never the client company's."""
        for lead in self:
            lead.email_from = lead.email_from

    @api.depends('partner_id.phone')
    def _compute_phone(self):
        """POC Phone is the person's, never the client company's."""
        for lead in self:
            lead.phone = lead.phone

    def _inverse_email_from(self):
        """The POC's email stays on the opportunity; the client company keeps
        its own."""

    def _inverse_phone(self):
        """The POC's phone stays on the opportunity; the client company keeps
        its own."""

    @api.depends('email_from', 'partner_id')
    def _compute_partner_email_update(self):
        # Drives CRM's "this will update the customer" hint, which no longer
        # applies now that nothing is written back.
        self.partner_email_update = False

    @api.depends('phone', 'partner_id')
    def _compute_partner_phone_update(self):
        self.partner_phone_update = False

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

    @api.depends(*[
        'poc%d_%s' % (n, suffix)
        for n in (2, 3, 4, 5)
        for suffix in POC_SUFFIXES
    ])
    def _compute_show_poc(self):
        """Open every block up to the last one that holds anything.

        A block is revealed when it has something in it or when any block
        after it does, so an opportunity whose only extra POC is the fourth
        opens 2, 3 and 4 - there is no way to reach block 4 with 2 and 3
        closed.

        Every field in a block counts, not just the name. A block holding
        only a phone number is still a block with data in it, and hiding it
        would leave that number saved and invisible.
        """
        for lead in self:
            filled = [
                any(lead['poc%d_%s' % (n, suffix)] for suffix in POC_SUFFIXES)
                for n in (2, 3, 4, 5)
            ]
            # Index 0 is POC 2: reveal it if it, or anything past it, is filled.
            for index, n in enumerate((2, 3, 4, 5)):
                lead['show_poc%d' % n] = any(filled[index:])

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
        if 'stage_id' in vals and any(lead.stage_id.id != vals['stage_id'] for lead in self):
            # The condition CRM itself restarts date_last_stage_update on.
            vals.setdefault('stage_reminder_sent_days', 0)
        res = super().write(vals)
        self._check_required_numbers(vals)
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
    # Every email goes to the users picked for its kind in CRM settings plus
    # the opportunity's own BDAs. Only opportunities: leads raised by the mail
    # alias or the website form would otherwise mail everyone about records
    # nobody has looked at yet.

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

    def _get_bda_users(self):
        # Archived BDAs are still on the record; read them, the mailer drops them.
        return self.sudo().with_context(active_test=False).bda_ids

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

    @staticmethod
    def _plain_number(value):
        """A number as entered: 1200000 stays 1200000 (:g would give
        1.2e+06), and 12.50 drops its trailing zero to 12.5."""
        return f'{value or 0:f}'.rstrip('0').rstrip('.')

    def _selection_label(self, fname):
        return dict(self._fields[fname]._description_selection(self.env)).get(self[fname], '')

    def _get_mail_details(self):
        """The opportunity's key facts, formatted for every CRM email."""
        self.ensure_one()
        lead = self.sudo()
        if lead.commercial_basis == 'lpm':
            commercial = _('%s lakhs / month', self._plain_number(lead.bill_rate_lpm)) if lead.bill_rate_lpm else ''
        else:
            commercial = f'{self._plain_number(lead.commercial_agreement_pct * 100)}%' if lead.commercial_agreement_pct else ''
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
            'expected_closure': self._short_date(self.env, lead.date_deadline),
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
                    email_values={'recipient_ids': [(6, 0, partners.ids)]},
                    force_send=False,
                )
            return True
        except Exception:
            _logger.exception("CRM notification %s failed for opportunity %s.",
                              template_xmlid, self.id)
            return False

    # ── Change notifications ──────────────────────────────────────
    def _get_change_partners(self):
        """Settings list plus this opportunity's BDAs, or nobody while the
        change notifications are off."""
        if not self._notify_enabled('crm_consulting.change_notify'):
            return self.env['res.partner']
        users = self.env.company.sudo().crm_change_recipient_ids | self._get_bda_users()
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
            return self._plain_number(value)
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
        if not leads or not self._notify_enabled('crm_consulting.change_notify'):
            return
        partners = self._mail_partners(
            self.env.company.sudo().crm_change_recipient_ids | leads._get_bda_users())
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
                    'recipient_ids': [(6, 0, partners.ids)],
                    'auto_delete': True,
                })
        except Exception:
            # A notification must never block the deletion it reports on.
            _logger.exception("CRM deletion notification failed for %s.", leads.ids)

    # ── Stuck-in-stage reminders ──────────────────────────────────
    @api.model
    def _cron_send_stage_reminders(self):
        """Remind about active clients' opportunities stuck in one stage.

        A mark is reached once the opportunity has been in its stage that
        many days or more. The one sent is the furthest mark reached, and only
        if it is further than what already went out - so a repeated run is a
        no-op, and after downtime one reminder catches up rather than a
        backlog of them.
        """
        if not self._notify_enabled('crm_consulting.stage_reminders'):
            return True
        days = self._get_reminder_days(STAGE_REMINDER_DAYS_PARAM)
        if not days:
            return True
        today = fields.Date.context_today(self)
        leads = self.search([
            ('type', '=', 'opportunity'),
            ('client_status', '=', 'active'),
            ('stage_id.stage_reminders', '=', True),
            ('date_last_stage_update', '<=', fields.Datetime.subtract(
                fields.Datetime.now(), days=min(days))),
        ])
        settings_users = self.env.company.sudo().crm_stage_reminder_recipient_ids
        for lead in leads:
            entered = lead.date_last_stage_update.date()
            in_stage = (today - entered).days
            reached = [d for d in days if in_stage >= d]
            if not reached:
                continue
            mark = max(reached)
            if mark <= lead.stage_reminder_sent_days:
                continue
            later = [d for d in days if d > in_stage]
            next_mark = min(later) if later else 0
            sent = lead._send_lead_mail(
                'crm_consulting_customization.mail_template_crm_lead_stuck',
                self._mail_partners(settings_users | lead._get_bda_users()),
                {'crm_stuck': {
                    'days': in_stage,
                    'accent': '#C0392B' if in_stage >= 15 else '#D68910',
                    'entered_on': self._long_date(self.env, entered),
                    'next_mark': next_mark,
                    'next_on': self._short_date(
                        self.env, fields.Date.add(entered, days=next_mark)) if next_mark else '',
                }},
            )
            if sent:
                # Not tracked, so this write sends no change email of its own.
                lead.stage_reminder_sent_days = mark
        return True
