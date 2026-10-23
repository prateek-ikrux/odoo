# CRM Consulting Customization

Reshapes Odoo CRM around a recruitment and consulting business: a four-stage
pipeline, engagement commercials in rupees, and POCs held on the
opportunity. Access is CRM's own Sales privilege, widened so that every BDA
on an opportunity sees it.

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
| POC Location | `poc1_location` | Char | Yes |
| POC LinkedIn | `poc1_linkedin` | Char, url widget | No (19.0.1.17.0) |
| Client Status | `client_status` | Selection: Active / Inactive / Hold | Yes |
| Start Date | `start_date` | Date (19.0.1.27.0) | No |
| End Date | `end_date` | Date, not before the Start Date (19.0.1.27.0) | No |
| Engagement Type | `engagement_type` | Selection: FTE / Consulting / FTE\|Consulting | Yes |
| Commercial Basis | `commercial_basis` | Selection: Percentage / Lakhs per Month | No (set from Engagement Type) |
| Commercial Agreement | `commercial_agreement_pct` | Float, percentage widget | No |
| Bill Rate | `bill_rate_lpm` | Float, lakhs per month | No |
| Open Positions | `open_positions` | Integer | No |
| Roles Open | `roles_open` | Integer | No |
| Project Duration | `project_duration` | Integer, months | No |
| Requirement Received | `milestone_requirement_received` (+ `_date`) | Boolean | No |
| Delivery Started | `milestone_delivery_started` (+ `_date`) | Boolean | No |
| Agreement Signed | `milestone_agreement_signed` (+ `_date`) | Boolean | No |
| Client Type | `client_type` | Many2one to the Client Types list | Yes |
| Industry / Domain | `industry_domain` | Many2one to the Industries / Domains list | No |
| POCs | `poc_ids` | List of `crm.lead.poc` (Name, Designation, Phone Number, Email, Location, LinkedIn), no limit; the first is the primary (19.0.1.26.0) | At least one; Name, Designation and Location on each row |

Existing fields are relabelled rather than duplicated wherever one already
said the same thing:

| Shown as | Is really | Why it was not a new field |
|---|---|---|
| Client Name | `name` | The opportunity's own title is the client's name (19.0.1.15.0) |
| **BDA** | `bda_ids`, replacing Salesperson on the form | Salesperson and BDA are one idea, so one field |
| POC Name | `contact_name` | The person being dealt with **is** the primary POC |
| Designation | `function` | |
| Phone Number | `phone` | Keeps Send SMS working on the primary POC |
| Email | `email_from` | Keeps Send Email working on the primary POC |

These four, with `poc1_location` and `poc1_linkedin`, are off the form since
19.0.1.26.0: they hold a copy of the primary POC - the first in the POC list -
and follow it whenever the list changes, so CRM's lists, the pipeline card,
Send Email and Send SMS keep showing the primary contact.

**Client Name is the opportunity's title.** Since 19.0.1.15.0 the client's
name is typed into the title at the top of the form, relabelled Client Name in
the form, list, search and import. CRM's customer link (`partner_id`, now
labelled Client Company) is off every view and no longer required; it is kept,
hidden, so opportunities that already point at a company keep that link.

**The customer link and the POCs are kept apart.** The customer link only
offers companies; a POC is a person at it. CRM normally treats them as
one party - picking a customer copies its name, email and phone into the
contact fields, and editing the contact's email or phone writes them back onto
the customer. Both directions are switched off (19.0.1.12.0), so choosing a
client never fills in the POC and a POC's details never overwrite the
company's.

Mandatory on the opportunity form (19.0.1.16.0): **Client Name**, **Client
Type**, **BDA**, **Client Status**, **Engagement Type**, and at least one POC,
each asking for **Name**, **Designation** and **Location**. LinkedIn became optional on every POC in 19.0.1.17.0.
Everything else is optional, and a Lost Reason is asked
for only when an opportunity is marked lost from the form, so a bulk import of
lost deals is not blocked by it.

The priority stars that CRM puts beside the closing date are off the form. The
column is untouched, so stars already given are kept.

### Possible duplicate opportunities (19.0.1.29.0)

A client should have one opportunity per engagement type, but nothing is
refused. Saving an opportunity from a form - a new one, or one whose Client
Name or Engagement Type changed - first asks the server what CRM already
holds for that client or a like-named one. If anything, a **Possible
duplicate opportunity** popup lists each match with its engagement type,
BDAs and stage, marked *same client and engagement type*, *same client,
different engagement type* or *similar client name*, and suggests asking to
be added as a BDA on it instead:

- **Save Anyway** saves as usual.
- **Discard Changes** reverts the unsaved changes - a new opportunity back
  to a blank form.
- Closing the popup goes back to editing with the changes kept.

The popup is `static/src/client_duplicate_check.js`, asking
`crm.lead.get_client_duplicate_message`. A form with a required field still
empty shows Odoo's own message first and the popup on the next save. An
import has no popup and goes through; **Pipeline > Filters > Possible
Duplicates** (`is_possible_duplicate`) lists every opportunity sharing its
client and engagement type with another one that is not lost.

- **Same client** compares the Client Name with case, spaces, punctuation
  and a trailing legal form (Pvt, Private, Ltd, Limited, Inc, LLP, LLC, PLC,
  Corp, Corporation, GmbH) taken out: "Birlasoft", "Birla Soft" and
  "Birlasoft Pvt. Ltd." are one client. It is kept in `client_key`.
- **Same engagement type** is exact. FTE/Consulting - a Consulting client
  absorbing the candidate through FTE - is a type of its own, so it sits
  beside an FTE and a Consulting opportunity for the same client.
- **Every opportunity counts** - won and open, and other BDAs' that the user
  cannot see - **except lost ones**: a client coming back after a lost deal
  starts a new opportunity without a popup about the old one.
- **Similar client name** is a name that contains, or is contained in, the
  one entered - "ITC" and "ITC (FlyDubai)" - often a separate account.

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
address belong to the client record, the contact
name and job position were the primary POC, and campaign, medium and source
are marketing, which is out of scope. The one thing worth keeping, how the
client is classified, is now on the front page.

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

### Exporting POCs

**CRM > Reporting > Export POCs** (19.0.1.22.0) downloads an Excel sheet with
one row per POC: Client Name, POC Name, Designation, Mobile Number, Email,
Location and LinkedIn. Every POC is included, the primary first; an empty
one is skipped.

Every filter is optional: clients, Client Type, Industry / Domain, Client
Status, Engagement Type, stage, BDA and a Start Date range. Lost
opportunities are left out unless **Include Lost Opportunities** is ticked,
and **Primary POC Only** limits the sheet to each client's first POC. Selecting opportunities in
the list and choosing **Actions > Export POCs** starts with just those clients.

The export follows CRM's own access rules, so a salesperson exports only the
clients they can already see in the pipeline.

### Who receives emails

Change notifications and activity reminders follow one hierarchy
(19.0.1.25.0), set up under **CRM > Configuration > Settings > Notification
Hierarchy**:

| Level | Who | Set in |
|---|---|---|
| Leadership | The people picked under **Leadership** | CRM settings |
| Managers | The **Team Leader** of each sales team | CRM > Configuration > Sales Teams |
| BDAs | The members of each sales team | CRM > Configuration > Sales Teams |

Someone on two levels counts at the higher.

- **Change notifications** (19.0.1.29.0) always go to the opportunity's
  BDAs - co-BDAs included, and any BDA the change took off it. Then a BDA's
  change also goes to their own team leader and leadership, a manager's to
  the BDAs' team leaders and leadership, leadership's to the BDAs' team
  leaders. Never to the person who made it. Adding, editing, removing or
  reordering POCs counts as a change: the POC list is tracked through
  `poc_summary` (POC List), and the email shows only the POC lines that
  changed. While change notifications are on, Odoo's own "You have been
  assigned" email is left out for opportunities - the new Primary BDA is a
  BDA, so the change notification already tells them.
  A change made by a scheduled job has nobody behind it, so it goes to the
  opportunity's BDAs, their team leaders and leadership.
- **Activity reminders** go to the person the activity is assigned to, and
  above them to their team leader and leadership - each a tick, both on to
  start. An activity assigned to nobody is the opportunity's BDAs' to do.

A BDA in no sales team has no manager, so their changes reach leadership
only. CRM settings list every BDA on an opportunity who has no team leader,
under Notification Hierarchy. The upgrade to 19.0.1.25.0 makes whoever was on the change
notification **Send to** list Leadership, and drops the activity reminder
list and the BDA, team leader, assignee and upward-only ticks.

**Email Tagged Colleagues** works outside the hierarchy: anyone tagged with
@ in an opportunity's chatter gets an email saying who tagged them, on which
opportunity, in a message or an internal note, with the message itself and
an **Open Opportunity and Reply** button (19.0.1.27.0). It replaces the bare
email Odoo would otherwise send them, whatever their own notification
preference, and the message stays in their Odoo Inbox too.

The stuck-in-stage report is a weekly summary, not news of one person's
work, so it keeps its own **Send to** list, which starts empty; **Select
everyone** puts every internal user with an email address on it and
**Clear** empties it.

### Stuck-in-stage report

One email a week replaces the per-opportunity stuck reminders (19.0.1.23.0).
Under **CRM > Configuration > Settings > Stuck-in-Stage Report**:

- **Send every** - the weekday it goes out on, at midnight at the start of
  that day, in the timezone of whoever last saved the settings.
- **Stuck after** - the days in one stage that put a client on the list,
  counted to the day the report goes out. An opportunity that last moved on a
  Monday has been 7 days in stage on the following Monday.
- **Send to** - who gets it. **Send now** sends it immediately, as of today.

The attached sheet lists every active client's opportunity in a stage that is
included (**CRM > Configuration > Stages > Include in Stuck-in-Stage Report**;
the won stage starts left out), longest in stage first, with BDAs, POC,
next activity and a link to each. A week with nobody stuck still sends a short
email saying so, with nothing attached.

### POCs: one list, no limit (19.0.1.23.0, 19.0.1.26.0)

An opportunity takes as many POCs as it needs, every one of them a row in the
**POCs** list, added with **Add a POC** and dragged into order by the handle.
The first row is the primary contact; drag another to the top to make them
primary. The **POC** search in the pipeline looks through all of them.

19.0.1.23.0 replaced the fixed POC 2 to 5 blocks with a list, moving whatever
was in them into it in order. 19.0.1.26.0 took POC 1 off the form too: the
upgrade makes each opportunity's POC 1 the first row of its list, ahead of
the rest. The opportunity's contact fields stay as a copy of the primary POC
(see the table of relabelled fields above).

**Bulk upload.** Use Odoo's standard format for a list: columns
`poc_ids/name`, `poc_ids/designation`, `poc_ids/phone`, `poc_ids/email`,
`poc_ids/location` and `poc_ids/linkedin`, with one row per POC - the first
(the primary) on the opportunity's own row, each further one on a row of its
own below it with every opportunity column left blank.

The older POC 1 columns (`contact_name`, `function`, `phone`, `email_from`,
`poc1_location`, `poc1_linkedin`) still load: on a new opportunity they become
the first POC, ahead of any `poc_ids` rows, and on an existing one they update
its primary POC. So `crm_bulk_upload_template_v3.xlsx`, which uses both, keeps
working.

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

Both are set on the opportunity, on the front page next to the client. Client
Type is mandatory; Industry / Domain is optional. Nothing is read from or written to the client record — the same
company can be classified one way on one opportunity and another way on the
next, and neither affects the other.

Both are picked from a master list:

- **CRM > Configuration > Pipeline > Client Types**
- **CRM > Configuration > Pipeline > Industries / Domains**

Add, rename and drag to reorder entries there; the opportunity dropdown follows.
The dropdown cannot create entries itself, so a report only ever groups into
buckets someone chose on purpose. Two entries cannot share a name.

An entry already used by an opportunity cannot be deleted. **Archive** it
instead: it leaves the dropdown, and the opportunities on it keep it. Each
list shows how many opportunities use an entry, with a button to open them.

The starting entries are seeded once, on install or on the upgrade to
19.0.1.19.0, and are not reset by later upgrades. Bulk-upload sheets fill
both columns by entry name, exactly as they did before.

---

## Notes for whoever maintains this

- **Commercial Agreement is one label over two columns.** The form always
  calls it Commercial Agreement and writes the unit immediately after the
  figure, with nothing in front of it — `%` for a percentage deal, `LPM`
  for a lakhs-per-month one. Which of the two is on screen follows the
  Commercial Basis, so a blended FTE/Consulting engagement shows whichever way
  it was actually struck. Behind it, `commercial_agreement_pct` and
  `bill_rate_lpm` are still two separate columns, because a percentage and a
  rate cannot share one; an export sees both.

- **Commercial Agreement is stored as a fraction.** 8% is held as `0.08`. That
  is what Odoo's percentage widget reads and writes. Anything reading the field
  directly — an export, a formula, a report — has to multiply by 100.

- **Bill Rate is a Float, not a Monetary.** It is a count of lakhs per month,
  which is not a currency: as a Monetary it rendered the company symbol in
  front of the figure, so 2.5 lakhs per month read as `₹ 2.50`. The unit is
  written after the figure instead, the way any other unit is. Explicit
  `digits=(16, 2)` keeps the same `numeric` column Monetary used, so the change
  moved no data. It is still a unit of lakhs — do not sum it against a rupee
  figure.

- **Dates read "21st July 2024" via a widget, not a language setting.**
  Neither strftime nor Luxon has a token for the ordinal suffix — `%d` and
  `d` both give `21` — so no `res.lang` date format can express this and the
  string is built in the browser. `static/src/ordinal_date_field.js` registers
  `ordinal_date`, which subclasses Odoo's own date field and overrides the one
  method every rendering goes through.

  Only the *displayed* string changes. Odoo's template already draws a focused
  date field as a real `<input>` and everything else as text, so typing,
  parsing and the date picker are untouched. The hover tooltip stays numeric,
  which is the one place the long form would not help.

  It is on this module's five date fields: Start Date, End Date and the
  three milestone dates. Dates elsewhere in Odoo are
  unaffected. The milestone dates carried a `numeric` option for the stock
  widget's habit of dropping the year from a date in the current year; this
  one always writes day, month and year, so the option went with it.

- **`bda_ids` always contains the owner.** Setting the salesperson adds them to
  the BDA list automatically, so ownership is one list to consult rather than a
  union to remember.

  Opportunities that predate the module are repaired on install by
  `post_init_hook`, and on upgrade by `migrations/19.0.1.1.0/post-migrate.py`;
  both call the same function. Only the owner is filled in, because nothing in
  the database records who else worked the account. An opportunity that never
  had an owner is left empty, and the form asks for a BDA the next time it is
  saved.

- **Client Type and the POCs are mandatory on the form, not on the field.** `crm.lead` also backs leads raised by the incoming-mail
  alias and the website form, and neither of those can answer all of them.
  A requirement on the field would reject them outright, so the rule is written
  on the opportunity form, which is the only way a person creates one.

  A lead that arrives by email can therefore reach the pipeline unclassified.
  It gets classified the first time somebody opens and saves it.

- **Required numbers would be held on the server.** None is required today:
  Open Positions, Roles Open and Commercial Agreement became optional in
  19.0.1.13.0 and Project Duration in 19.0.1.16.0. The mechanism stays for
  when one is wanted again: Odoo's web client lets a 0 through as filled in,
  so `_check_required_numbers` refuses a zero for any number listed in
  `REQUIRED_NUMBERS` — for the numbers being written, plus those listed
  whenever the engagement type or commercial basis changes. A new opportunity from the form sends every number and is checked
  in full; a lead from the mail alias sends none of them and a kanban drag
  sends only the stage, so neither is refused. An older opportunity still
  holding a 0 is only held to the rule once one of those numbers is edited.

- **Client Type and Industry / Domain used to live on the company.** Up to
  1.2.0 they were company fields mirrored onto the opportunity. As of 1.3.0
  they are the opportunity's own and `res.partner` does not carry them at all.
  `migrations/19.0.1.3.0/pre-migrate.py` sweeps anything the mirror had not
  picked up across before the company columns go.

  The classification of a company with no opportunity has nowhere to land and
  is not carried over. Take a copy of `res_partner.client_type` and
  `res_partner.industry_domain` before upgrading if those matter.

- **Roles and reporting were removed in 19.0.1.8.0.** While it carried them,
  this module rewrote two record rules and two action contexts belonging to
  `crm`, and shipped its own groups, `ir.model.access` rows, seven reports and
  a nightly ageing cron.

  Its own records go when the upgrade finds no data file claiming them, but
  three kinds do not: the two `crm` rules (no-update there, so a `crm` upgrade
  will not restore them), the two `crm` action contexts (only reapplied when
  `crm` itself is upgraded) and this module's own cron (no-update here, and a
  stale no-update record is left alone rather than deleted — it would have
  gone on calling a method that no longer exists). All three are undone by
  `migrations/19.0.1.8.0/post-migrate.py`, which is safe to re-run.

  Users were **not** given anything in exchange for the roles they lost, so
  anyone who had one has no Sales access until it is granted by hand under
  Settings. `days_in_current_stage` and `signed_cycle_days` went with the
  reports; Odoo leaves their columns in place, so the history is still there
  to read and to drop by hand.

- **Expected Revenue and Salesperson are hidden, not deleted, in the list and
  kanban views.** CRM's own Forecast and My Activities views are built on top of
  those and reach for those exact nodes; deleting one stops that view being
  built at all.

- **Client Type and Industry / Domain became master lists in 19.0.1.19.0.**
  They were selections; they are now many2ones to `crm.client.type` and
  `crm.industry.domain`, under the same field names so import sheets and saved
  filters keep working. `migrations/19.0.1.19.0/pre-migrate.py` moves each old
  column of codes aside before the module loads, and `post-migrate.py` points
  every opportunity at the seeded entry for its code (external ids
  `client_type_<code>` and `industry_domain_<code>`), then drops the old
  columns. A code with no seeded entry gets one of its own, named after the
  code. Past chatter tracking keeps the old labels as text.

  The pre-migrate also deletes the old selection options. Some Odoo 19 builds
  otherwise fail at the very end of the upgrade with `AttributeError: 'str'
  object has no attribute 'get'` - after the migration and the new version
  are already committed, so a retry skips the 19.0.1.19.0 scripts and fails
  again. `migrations/19.0.1.20.0/pre-migrate.py` repeats that clean-up for a
  database left in that state.

- **Client Status was reworked in 19.0.1.18.0.** Active / Dormant / Passive
  became Active / Inactive / Hold. `migrations/19.0.1.18.0/pre-migrate.py`
  moves every Dormant and Passive opportunity to Inactive before the old
  values go; Active is untouched. The chatter keeps the old values in past
  tracking messages. A bulk-upload sheet or saved filter still using Dormant
  or Passive has to follow.

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
