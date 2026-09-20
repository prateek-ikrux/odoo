# CRM Consulting Customization

Reshapes Odoo CRM around a recruitment and consulting business: a four-stage
pipeline, engagement commercials in rupees, POCs held on the
opportunity, and four roles that divide who may see and do what.

Built and tested against **Odoo 19.0 Community**.

---

## Install

1. The module lives in the addons path already configured in `odoo.conf`:

   ```
   C:\projects\odoo\odoo\custom_addons\crm_consulting_customization
   ```

2. Install it:

   ```
   odoo-bin -c odoo.conf -d <database> -i crm_consulting_customization --stop-after-init
   ```

   Upgrading later uses `-u` in place of `-i`.

3. Give each person a role. **Settings > Users & Companies > Users**, open a
   user, and pick one of BDA, Sales / Sales Head, Leadership or Admin under the
   **CRM Consulting** privilege. Nobody has a role until you give them one.

`crm`, `contacts` and `sales_team` are pulled in as dependencies if they are not
already installed.

---

## What changes

### Pipeline

The four stages CRM ships are rewritten into New, Initial Outreach, Follow-up in
Progress and Agreement / MSA Signed. They are rewritten, not replaced, so no
opportunity has to be moved and nothing is deleted.

Every stage change is recorded in the opportunity's chatter with its date.
**Days in Current Stage** and CRM's own **Status time** breakdown both read from
that record.

Closed-lost is a status, not a stage. An opportunity marked lost keeps the stage
it died in — which is what makes the conversion funnel show where deals are
actually lost — and a lost reason is now mandatory.

### Fields added to an opportunity

| Label | Technical name | Type | Required |
|---|---|---|---|
| BDA | `bda_ids` | Many2many to users | Yes |
| POC Location | `poc1_location` | Char | No |
| POC LinkedIn | `poc1_linkedin` | Char, url widget | No |
| Client Status | `client_status` | Selection: Active / Dormant / Passive | Yes |
| Initial Outreach Date | `initial_outreach_date` | Date | Yes |
| Engagement Type | `engagement_type` | Selection: FTE / Consulting / FTE\|Consulting | Yes |
| Commercial Basis | `commercial_basis` | Selection: Percentage / Lakhs per Month | No |
| Commercial Agreement | `commercial_agreement_pct` | Float, percentage widget | Never |
| Bill Rate | `bill_rate_lpm` | Monetary, ₹ lakhs per month | No |
| Open Positions | `open_positions` | Integer | No |
| Roles Open | `roles_open` | Integer | No |
| Project Duration | `project_duration` | Integer, months | No |
| Requirement Received | `milestone_requirement_received` (+ `_date`) | Boolean | No |
| Delivery Started | `milestone_delivery_started` (+ `_date`) | Boolean | No |
| Agreement Signed | `milestone_agreement_signed` (+ `_date`) | Boolean | No |
| Days in Current Stage | `days_in_current_stage` | Integer, computed | — |
| Outreach to Signature | `signed_cycle_days` | Integer, computed | — |
| Client Type | `client_type` | Selection | Yes |
| Industry / Domain | `industry_domain` | Selection | Yes |
| POC 2–5 | `poc2_name` … `poc5_linkedin` | 4 × (Name, Designation, Phone Number, Email, Location, LinkedIn) | No |

Existing fields are relabelled rather than duplicated wherever one already
said the same thing:

| Shown as | Is really | Why it was not a new field |
|---|---|---|
| Client Name | `partner_id` | The client is the opportunity's customer |
| Expected Closure Date | `date_deadline` | Native forecasting already reads it |
| **BDA** | `bda_ids`, replacing Salesperson on the form | Salesperson and BDA are one idea, so one field |
| POC 1 → Name | `contact_name` | The person being dealt with **is** the primary POC |
| POC 1 → Designation | `function` | |
| POC 1 → Phone Number | `phone` | Keeps Send SMS working on the POC |
| POC 1 → Email | `email_from` | Keeps Send Email working on the POC |

Only **Location** and **LinkedIn** are genuinely new on POC 1.

### Salesperson and BDA

They are the same idea, so the form shows one field: **BDA**, which takes as
many people as the account needs.

Odoo's own `user_id` still exists underneath, relabelled **Primary BDA**,
because CRM needs a single name for an activity assignment, for whose pipeline
an opportunity counts in, and for the avatar on the kanban card. It is not a
second field to fill in and it is not on the form — it follows the BDA list:

- Naming BDAs sets the Primary BDA to the first of them.
- Adding another BDA does **not** reassign the opportunity.
- Removing the Primary BDA from the list hands it to someone still on it.

### The Contacts tab

Removed. Everything on it was already somewhere better — the company name and
address belong to the client record that Client Name points at, the contact
name and job position were the primary POC, and campaign, medium and source
are marketing, which is out of scope. The one thing worth keeping, how the
client is classified, is now on the front page beside Client Name.

The opportunity form is left with a single **Notes** tab; everything else is on
the main screen.

### Fields removed from the opportunity form

**Expected Revenue**, the commercial **Probability**, and the generic
**Properties** placeholders are all off the form.

None of the underlying columns were dropped — the data is intact and still
exportable. `probability` in particular still drives CRM's own won/lost
computation behind the scenes, which is why it is hidden rather than deleted.

### Company and POC records

- **Location** (city or site) added to both.
- **Website** relabelled **LinkedIn** on both. There is no separate website field.
- **Job Position** relabelled **Designation**. There is no separate job-description field.
- The **Contacts** section is now **POCs**, and every POC captures phone,
  designation and location.

### Reporting

Seven reports under **CRM > Reporting**: Pipeline by Stage, Opportunities by
Client, Conversion Funnel, Ageing, Engagement Milestones, BDA Activity and
Closed-Lost Analysis.

All of them are ordinary list, pivot and graph views. Every stage breakdown
groups by the stage field, never by a stage's name, so renaming or reordering a
stage simply relabels or moves a column.

### Access

| Role | Create | Read | Edit | Delete | Reports | Config |
|---|---|---|---|---|---|---|
| BDA | Yes | Own opportunities only | Own | No | Own pipeline | No |
| Sales / Sales Head | Yes | All | All | No | All | No |
| Leadership | Yes | All | All | No | All | No |
| Admin | Yes | All | All | Yes | All | Yes |

Delete is denied in `ir.model.access.csv`, not merely hidden — attempting it
raises an access error. Archive an opportunity or mark it closed-lost instead.

"Own" means the user is the owner **or** appears in the BDA list. A BDA does not
see unassigned opportunities, and this holds in list views, search, reports and
exports alike, because it is enforced by a record rule rather than by a filter.

Permissions depend on role and ownership only. Nothing is tied to a stage.

---

## Changing things without a developer

### Stages

**CRM > Configuration > Stages.** Rename, reorder, add or delete freely.
Nothing in this module refers to a stage by name or by identifier, so none of it
breaks.

The one thing a stage carries that behaviour depends on is **Is Won Stage?**.
Tick it on whichever stage means the deal is closed and won; it is currently on
Agreement / MSA Signed.

The four stages are seeded once, when the module is installed. Upgrading the
module afterwards leaves them alone, so your renames and reorderings survive.

### Open Positions and Roles Open

Two counts, and they answer different questions. **Open Positions** is how many
vacancies the engagement has; **Roles Open** is how many distinct roles those
vacancies span. Ten openings across three roles is `10` and `3`. Neither is
configured anywhere — both are typed on the opportunity.

### Lost reasons

**CRM > Configuration > Lost Reasons.** Add your own, or archive the ones you do
not use. The reason is required whenever an opportunity is marked lost.

### Client Type and Industry / Domain

Both are set on the opportunity, on the front page next to the client, and both
are mandatory. Nothing is read from or written to the client record — the same
company can be classified one way on one opportunity and another way on the
next, and neither affects the other.

The lists are fixed, deliberately — a report only groups cleanly into buckets
that cannot be typed freehand. Changing them is a one-line edit in
`models/crm_lead.py`, in the `CLIENT_TYPES` and `INDUSTRY_DOMAINS` lists at the
top of the file, followed by a module upgrade.

Add to the end of a list to be safe. Changing the code of an existing entry (the
left-hand value) orphans the records already using it; changing only its label
(the right-hand text) is always safe.

---

## Notes for whoever maintains this

- **Commercial Agreement is one label over two columns.** The form always
  calls it Commercial Agreement and writes the unit next to the figure — `%`
  for a percentage deal, `₹ … LPM` for a lakhs-per-month one. Behind it,
  `commercial_agreement_pct` and `bill_rate_lpm` are still two separate
  columns, because a percentage and a rupee figure cannot share one. Only the
  one the Commercial Basis calls for is ever on screen; an export sees both.

- **Commercial Agreement is stored as a fraction.** 8% is held as `0.08`. That
  is what Odoo's percentage widget reads and writes. Anything reading the field
  directly — an export, a formula, a report — has to multiply by 100.

- **Bill Rate is in lakhs per month, not rupees.** It is a monetary field in the
  company currency, so a bill rate of 2.5 lakhs per month displays as `₹ 2.50`.
  It is a unit of lakhs, so do not sum it against a rupee figure.

- **`days_in_current_stage` is refreshed nightly** by the scheduled action *CRM:
  age opportunities in their current stage*. Between runs it can be up to a day
  behind. It is stored rather than computed live so that the ageing report can
  sort and average on it.

- **`bda_ids` always contains the owner.** Setting the salesperson adds them to
  the BDA list automatically, so ownership is one list to consult rather than a
  union to remember.

  Opportunities that predate the module are repaired on install by
  `post_init_hook`, and on upgrade by `migrations/19.0.1.1.0/post-migrate.py`;
  both call the same function. Only the owner is filled in, because nothing in
  the database records who else worked the account. An opportunity that never
  had an owner is left empty, and the form asks for a BDA the next time it is
  saved.

- **Client Type, Industry / Domain and Client Name are mandatory on the form,
  not on the field.** `crm.lead` also backs leads raised by the incoming-mail
  alias and the website form, and neither of those can answer any of the three.
  A requirement on the field would reject them outright, so the rule is written
  on the opportunity form, which is the only way a person creates one.

  A lead that arrives by email can therefore reach the pipeline unclassified.
  It gets classified the first time somebody opens and saves it.

- **Client Type and Industry / Domain used to live on the company.** Up to
  1.2.0 they were company fields mirrored onto the opportunity. As of 1.3.0
  they are the opportunity's own and `res.partner` does not carry them at all.
  `migrations/19.0.1.3.0/pre-migrate.py` sweeps anything the mirror had not
  picked up across before the company columns go.

  The classification of a company with no opportunity has nowhere to land and
  is not carried over. Take a copy of `res_partner.client_type` and
  `res_partner.industry_domain` before upgrading if those matter.

- **The module rewrites two record rules that belong to CRM** —
  `crm.crm_rule_personal_lead` and
  `crm.crm_activity_report_rule_personal_activities`. Both shipped as "my
  records, plus everything unassigned", which leaks and knows nothing of
  `bda_ids`. They are rewritten in place because record rules from different
  groups are OR-ed: a second rule could only ever widen what a BDA sees, never
  narrow it. Reinstalling `crm` itself would restore Odoo's versions.

- **Expected Revenue and Salesperson are hidden, not deleted, in the list and
  kanban views.** CRM's own Forecast and My Activities views are built on top of
  those and reach for those exact nodes; deleting one stops that view being
  built at all.

- **Buyers became POCs in 19.0.1.4.0**, columns included.
  `buyer1_location` and the whole `buyer2_*`–`buyer5_*` block were renamed
  `poc*` in place by `migrations/19.0.1.4.0/pre-migrate.py`. The rename keeps
  the data where it is; letting the ORM add the new columns beside the old
  ones would not have. Anything reading the old names — an export template, a
  saved filter, an integration — has to follow.

- **Roles Open stopped being a tag list in 19.0.1.4.0.** It was a many2many to
  `crm.role.open`; it is now an integer. The same migration counts each
  opportunity's tags into it, so three tags reads as `3`, and the
  `crm.role.open` model, its seeded roles and its configuration menu go with
  the field.

  The `crm_role_open` and `crm_lead_role_open_rel` **tables** survive the
  upgrade. Odoo deregisters a model it no longer finds in the code but does
  not drop its table, and that is the outcome worth having here: the relation
  table is the only remaining record of which roles an opportunity was
  hiring for. Nothing reads either table. Drop them by hand once you are
  satisfied you do not want that history.

- **Tags are hidden, not removed.** `tag_ids` is off the form (both the lead
  and the opportunity side of it), the list, the search panel and both kanban
  cards — the pipeline one and the narrow one shown on a phone, which is a
  separate view and needed taking off in its own right. Nothing this module
  reports on reads it. The column is untouched, so anything already tagged
  keeps its tags and they stay exportable.

- **Four columns were folded away in 19.0.1.2.0.** POC 1 first
  shipped as `buyer1_name`, `buyer1_designation`, `buyer1_phone` and
  `buyer1_email` beside the four fields an opportunity already had for the same
  things. `migrations/19.0.1.2.0/pre-migrate.py` moves anything typed into them
  across before the fields go, and only where the destination is empty. Odoo
  drops the columns itself once the fields are gone.
