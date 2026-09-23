# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# The milestone flags, paired with the field that records when each was
# raised. Kept in one place so write() and the cycle-time computation stay in
# step with the field definitions instead of repeating the pairing.
MILESTONE_DATE_FIELDS = {
    'milestone_requirement_received': 'milestone_requirement_received_date',
    'milestone_delivery_started': 'milestone_delivery_started_date',
    'milestone_agreement_signed': 'milestone_agreement_signed_date',
}

# Both lists are selections rather than free text so that a report grouped by
# either one has a fixed, countable set of buckets. Extending a list is a
# one-line edit here; see the README for the procedure.
# The fields a POC block 2-5 is made of. Named once so _compute_show_poc
# cannot fall behind the field definitions below.
POC_SUFFIXES = ('name', 'designation', 'phone', 'email', 'location', 'linkedin')

CLIENT_TYPES = [
    ('product_isv', 'Product / ISV'),
    ('it_services', 'IT Services & Consulting'),
    ('gcc_captive', 'GCC / Captive'),
    ('staffing_partner', 'Staffing & Recruitment Partner'),
    ('startup', 'Startup'),
    ('enterprise_non_it', 'Enterprise (non-IT)'),
    ('others', 'Others'),
]

INDUSTRY_DOMAINS = [
    ('bfsi', 'BFSI'),
    ('healthcare', 'Healthcare & Life Sciences'),
    ('manufacturing', 'Manufacturing & Industrial'),
    ('retail_ecommerce', 'Retail & E-commerce'),
    ('telecom_media', 'Telecom & Media'),
    ('energy_utilities', 'Energy & Utilities'),
    ('logistics', 'Logistics & Transportation'),
    ('technology_saas', 'Technology & SaaS'),
    ('public_sector', 'Public Sector / Government'),
    ('others', 'Others'),
]


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

    partner_id = fields.Many2one(string='Client Name')

    # Client Type and Industry / Domain belong to the opportunity. They are
    # entered here and held here; nothing reads them off the client record, so
    # classifying a deal never means leaving CRM. Ordinary stored columns,
    # which is what the pivot groups by.
    #
    # Mandatory on the form rather than on the field, the same way Client Name
    # is. crm.lead also backs leads raised by the incoming-mail alias and the
    # website form, neither of which can answer these two, and a requirement
    # on the field would reject those outright. Everything a person creates
    # goes through a form, which is where the rule has to hold.
    client_type = fields.Selection(
        selection=CLIENT_TYPES,
        string='Client Type',
        index=True,
        tracking=True,
    )

    industry_domain = fields.Selection(
        selection=INDUSTRY_DOMAINS,
        string='Industry / Domain',
        index=True,
        tracking=True,
    )

    client_status = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('dormant', 'Dormant'),
            ('passive', 'Passive'),
        ],
        string='Client Status',
        required=True,
        default='active',
        tracking=True,
    )

    initial_outreach_date = fields.Date(
        'Initial Outreach Date',
        required=True,
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
    # POC contacts
    # -------------------------------------------------------------------
    # Five fixed blocks rather than a linked list: a POC belongs to the
    # opportunity that found them and is not meant to be reused across
    # opportunities. POC 1 is the primary contact; 2 to 5 are optional and
    # never validated.
    #
    # POC 1 is not a new set of fields. An opportunity already carries the
    # name, job position, email and phone of the person being dealt with, and
    # that person is the primary POC - so POC 1 is those fields, relabelled,
    # with only the location and the LinkedIn profile genuinely new. Keeping
    # them means the POC still fills in from the client record, still drives
    # Send Email and Send SMS, and still shows in CRM's own lists and reports.
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
        leads._sync_owner_from_bda()
        raised = {
            flag: True
            for flag in MILESTONE_DATE_FIELDS
            if any(vals.get(flag) for vals in vals_list)
        }
        if raised:
            leads._stamp_milestone_dates(raised)
        return leads

    def write(self, vals):
        res = super().write(vals)
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
