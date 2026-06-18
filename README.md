# Recruitment Pipeline Report

**Module Technical Name:** `recruitment_pipeline_report`
**Version:** `19.0.2.1.16`
**Odoo Compatibility:** Odoo 19
**License:** LGPL-3
**Dependencies:** `hr`, `hr_recruitment`, `hr_skills`

---

## Overview

This module extends Odoo 19's native recruitment module (`hr_recruitment`) with a comprehensive pipeline reporting system, enhanced applicant tracking, internal assessment reporting, and rich customisation across Job Positions, Applicants, Partners, and Departments. It introduces three exportable reports — Pipeline Summary, Applicant Tracker, and Internal Assessment Report — all available in both an interactive Odoo list/pivot view and as formatted Excel (.xlsx) downloads.

---

## Features

### 1. Pipeline Summary Report

A dedicated read-only SQL view (`recruitment.pipeline.summary.view`) aggregates applicants by Client (Department), Job Position, and Recruitment Stage, and exposes the data as both a **List view** and a **Pivot view** under Recruitment → Reporting → Pipeline Summary.

**List view columns:**
- Client, POC, Role, Role Type (FTE / Consulting), Role Status, Role Status Remarks, No. of Positions, Applicant Count

**Pivot view axes:**
- Rows: Client → POC → Role → Role Type → Role Status → Role Status Remarks
- Columns: Recruitment Stage (dynamic, all active stages)
- Measures: No. of Positions, Applicant Count

**Export to Excel (Pipeline Summary):**

Triggered via an "Export Excel" header button or an action button, this opens a wizard with filters before generating a styled `.xlsx` file:

- Filters: Date From / To, Clients (multi-select), Roles (multi-select), Role Status
- Output: Two-row grouped headers — primary identity columns (`#`, Client, POC, Role, Role Type, Role Status, Role Status Remarks, No. of Positions) in dark navy, and dynamic stage count columns under a merged "Pipeline Summary" header in steel blue
- Formatting: Frozen header rows, column auto-widths, border styling, alternating row hints

**Print to PDF:**

A "Print Report" action generates a PDF using a custom A3 Landscape paper format with styled HTML table rendering (colour-coded role type and status badges, stage counts, print timestamp).

---

### 2. Applicant Tracker

A rich list view of `hr.applicant` records (Recruitment → Reporting → Applicant Tracker) designed to give recruiters a full snapshot of every candidate across all requisitions, with all custom fields visible as optional columns.

**Columns (all optional/toggleable):**
- Requisition Details: Req ID, Client, Position / Role, Role Type, TE / Recruiter
- Application Details: Source, Application Date (ordinal format e.g. "2nd May 2026"), Current Status, Client Portal Status (colour-coded badge)
- Candidate Details: Candidate Name, Contact Number, Email ID, Skill, Total Experience, Relevant Experience, Current Organization, Designation, Education
- Location & Availability: Current Location, Preferred Location, Open to Anywhere, Notice Period, Last Working Date
- Compensation: Current CTC (LPA), Expected CTC (LPA), Budget (LPA), Bill Rate (LPM), Offer in Hand (LPA)
- Additional: Remarks

**Export to Excel (Applicant Tracker):**

An "Export Excel" header button opens a filtered wizard (Date From/To, Clients, Roles, Recruiters, Role Status) and generates a multi-section `.xlsx` file with colour-coded two-row grouped headers:

| Section | Header Colour |
|---|---|
| Requisition Details | Dark Navy `#1A3A5C` |
| Application Details | Dark Green `#1A6B4A` |
| Candidate Details | Dark Brown `#6B3A1A` |
| Location & Availability | Dark Purple `#4A1A6B` |
| Compensation | Dark Teal `#1A5C6B` |
| Additional Information | Dark Red `#5C1A1A` |

Special cell formatting: Client Portal Status is green (Uploaded) or red (Not Uploaded); Last Working Date shows "N/A" in muted italic when not applicable.

---

### 3. Internal Assessment Report

A list view of `hr.applicant` records (Recruitment → Reporting → Internal Assessment Report) focused purely on assessment tracking per candidate.

**Columns:**
- Req ID, Client, Role, Role Type, Role Status, Role Status Remarks
- Candidate Name
- Assessment Link Received (Yes/No badge)
- Assessment Taken (Yes/No badge)
- Assessment Feedback (Select/Reject badge)
- Current Hiring Status (current stage name)

**N/A cascade logic:** If Assessment Link Received = No, Assessment Taken and Assessment Feedback display as "N/A". If Assessment Taken = No, Assessment Feedback displays as "N/A".

**Export to Excel (Internal Assessment Report):**

Generates `Internal_Assessment_Report.xlsx` with single-row styled headers (blue on white), colour-coded Yes/No and Select/Reject cells, and frozen header rows.

---

### 4. Enhanced Job Position (`hr.job`)

The `hr.job` model is extended with the following custom fields:

| Field | Type | Description |
|---|---|---|
| `x_req_id` | Char | Requisition ID (e.g. `REQ-2024-001`) — manually entered |
| `x_employment_type` | Selection | FTE or Consulting |
| `x_role_status` | Selection | Active, In Progress, On Hold, Closed |
| `x_sub_status` | Selection | Candidate Drop, Drop by Client, On Hold Due to Alignment, N/A |
| `x_poc_id` | Many2one → `res.partner` | Point of Contact, filtered by the job's Client (Department) |
| `x_min_experience` | Integer | Minimum experience in years |
| `x_max_experience` | Integer | Maximum experience in years |
| `x_location_ids` | Many2many → `recruitment.city` | Available job locations |
| `x_skill_ids` | Many2many → `recruitment.skill` | Required skills for the role |
| `x_recruiter_ids` | Many2many → `res.users` | Assigned recruiters (replaces single `user_id`) |
| `x_budget_lpa` | Float | Budget in LPA (shown only for FTE roles) |
| `x_bill_rate_lpm` | Float | Bill rate in LPM (shown only for Consulting roles) |
| `x_display_name` | Char (computed) | Rich display label: `[REQ-001] Infosys - Python Developer \| FTE \| 2-4 Yrs` |

**Native `department_id` is relabelled "Client"** across all views.

**Recruiter sync logic:** `x_recruiter_ids` and native `user_id` are kept in sync — adding/removing recruiters automatically updates the responsible user, and vice versa.

**`create_action()` override:** After creating a Job Position, the form redirects back to the job's config page instead of the default kanban view.

**Job list view:** The native `name` column is replaced by `x_display_name` for richer context.

---

### 5. Enhanced Applicant Form (`hr.applicant`)

A large set of custom fields is added to the applicant record:

**Job position mirrors (read-only, stored, related):**
- `x_req_id` — Req ID
- `x_employment_type` — Employment Type
- `x_role_status` — Role Status
- `x_sub_status` — Role Status Remarks
- `x_poc_id` — POC
- `x_no_of_positions` — No. of Positions
- `x_min_experience` / `x_max_experience` — Experience range
- `x_job_location_ids` — Job's available locations (used to filter preferred locations)

**Candidate details:**
- `x_skill_ids` — Skills (from shared Skill master)
- `x_total_experience` — Total experience (e.g. "5.5 Yrs")
- `x_relevant_experience` — Relevant experience
- `x_current_organization` — Current employer
- `x_designation` — Current job title
- `x_education` — Highest qualification

**Location & availability:**
- `x_current_location_id` — Current city (from City master)
- `x_preferred_location_ids` — Preferred cities, filtered to job's available locations
- `x_open_to_anywhere` — Boolean flag for relocation openness
- `x_notice_period` — Selection: 30 Days, 60 Days, 90 Days, Immediate Joiner, Serving Notice Period
- `x_lwd` — Last Working Date (visible only when notice period is "Serving" or "Immediate Joiner"; auto-cleared on period change)

**Compensation:**
- `x_current_ctc_lpa` — Current CTC in LPA
- `x_expected_ctc_lpa` — Expected CTC in LPA
- `x_offer_in_hand_ids` — Competing offers (tags from `hr.applicant.offer.tag`)
- `x_budget_lpa_display` — Computed from job (FTE roles only)
- `x_bill_rate_lpm_display` — Computed from job (Consulting roles only)

**Assessment fields:**
- `x_assessment_link_received` — Yes/No
- `x_assessment_taken` — Yes/No
- `x_assessment_feedback` — Select/Reject

**Application tracking:**
- `x_client_portal_status` — Uploaded / Not Uploaded
- `x_reason_for_job_change` — Text
- `x_remarks` — Internal notes

**Date display:**
- `x_create_date_display` — Application date in ordinal format (e.g. "2nd May 2026")
- `x_lwd_display` — Last Working Date in same format

**Priority (5-star evaluation):** Native Odoo `priority` field (0–3 stars) is extended to a 0–5 scale for finer candidate evaluation.

**LinkedIn button:** The LinkedIn profile field uses a custom logo button (instead of Odoo's default URL icon) to open the URL in a new tab.

**Recruiter validation:**
- Onchange on `job_id` auto-restricts the recruiter dropdown to only recruiters assigned to that job, clears invalid selections, and pre-fills the first available recruiter.
- Onchange on `user_id` validates and warns if an unassigned recruiter is selected.
- A `@api.constrains` check prevents saving an applicant with a recruiter not in the job's recruiter list.

---

### 6. Master Data Models

**City Master (`recruitment.city`):**
- Maintains a unique list of city names used for candidate current location and preferred locations, and for job available locations.
- Accessible under Recruitment → Configuration → Master Data → Cities

**Skill Master (`recruitment.skill`):**
- Maintains a unique list of skill names shared between job required skills and candidate skills.
- Accessible under Recruitment → Configuration → Master Data → Skills

**Offer Tag (`hr.applicant.offer.tag`):**
- A tag model for recording competing offer amounts (LPA) on an applicant.

---

### 7. Partner (Contact) Enhancements

A `x_client_department_id` (Many2one → `hr.department`) field is added to `res.partner`, linking external contacts to a Client organisation. This field appears in both the partner form and list views and is used to filter the POC field on Job Positions.

---

### 8. Department (Client) Enhancements

A computed `x_poc_contact_count` field counts how many `res.partner` contacts are linked to a Department (Client). A smart button on the Department form opens a filtered list of those contacts.

---

## Security

All custom models and wizards are granted full CRUD access to users in the `hr_recruitment.group_hr_recruitment_user` group. The pipeline summary view is read-only for that group.

| Model | Access |
|---|---|
| `recruitment.pipeline.summary.view` | Read only |
| `recruitment.pipeline.summary.wizard` | Full (transient) |
| `recruitment.applicant.tracker.wizard` | Full (transient) |
| `recruitment.assessment.report.wizard` | Full (transient) |
| `recruitment.city` | Full |
| `recruitment.skill` | Full |
| `hr.applicant.offer.tag` | Full |

---

## Migration History

The module includes migration scripts for upgrades across the following versions:

| Version | Change |
|---|---|
| `19.0.2.1.0` | Migrated `x_role_status` and `x_sub_status` from `hr.applicant` to `hr.job` (role status moved to job level). Normalised free-text sub-status values to selection keys. |
| `19.0.2.1.1` | Sanitised legacy free-text role/sub-status values on both jobs and applicants. Resynced stored related fields. |
| `19.0.2.1.2` | Recomputed `x_display_name` (job display label) for all existing job positions. |
| `19.0.2.1.4` | Migrated POC from internal `res.users` to external `res.partner`. Backed up old user IDs, then mapped to partner records and linked their client departments. |
| `19.0.2.1.7` | Migrated recruiter from a Many2many (`x_recruiter_ids` m2m) to a Many2one (`x_recruiter_id`) on `hr.applicant`, picking the lowest-id recruiter per applicant. Cleaned up leftover relation tables. |
| `19.0.2.1.8` | Renamed `x_rec_id` → `x_req_id` on both `hr.job` and `hr.applicant`. |
| `19.0.2.1.9` | Added `x_assessment_link_received`, `x_assessment_taken`, and `x_assessment_feedback` columns to `hr.applicant`. |
| `19.0.2.1.10` | Converted `x_notice_period` from free-text Char to a Selection field. Mapped existing values ("30 days", "60 days", "90 days", "immediate joiner") to selection keys; all unrecognised values cleared to NULL. |
| `19.0.2.1.11` | Renamed recruitment stages: "Client Round" → "L3", "Client Round TBS" → "L3 TBS", etc. "TBO" → "To Be Offered". |
| `19.0.2.1.15` | Added "Serving Notice Period" to `x_notice_period` selection. Extended `priority` field from 0–3 to 0–5 stars. No schema changes required. |
| `19.0.2.1.16` | Cleared `x_lwd` (Last Working Date) for any applicants whose notice period does not warrant it (i.e. not `serving_notice` or `immediate_joiner`). |

---

## Module Structure

```
recruitment_pipeline_report/
├── __manifest__.py
├── models/
│   ├── pipeline_constants.py          # Shared selection lists and column headers
│   ├── pipeline_summary_view.py       # SQL view model (pivot/list)
│   ├── pipeline_summary_wizard.py     # Export wizard for Pipeline Summary
│   ├── pipeline_xlsx.py               # Excel builder for Pipeline Summary
│   ├── applicant_tracker_wizard.py    # Export wizard for Applicant Tracker
│   ├── applicant_tracker_xlsx.py      # Excel builder for Applicant Tracker
│   ├── assessment_report_wizard.py    # Export wizard for Assessment Report
│   ├── assessment_report_xlsx.py      # Excel builder for Assessment Report
│   ├── hr_applicant.py                # Applicant model extensions
│   ├── hr_job.py                      # Job position model extensions
│   ├── hr_department.py               # Department (Client) extensions
│   ├── hr_applicant_offer_tag.py      # Offer tag model
│   ├── recruitment_city.py            # City master model
│   ├── recruitment_skill.py           # Skill master model
│   └── res_partner.py                 # Partner (POC) extensions
├── views/
│   ├── hr_applicant_view_inherit.xml  # Applicant form/list/search extensions
│   ├── hr_job_view_inherit.xml        # Job position form/list extensions
│   ├── hr_department_view_inherit.xml # Department form extension (POC stat button)
│   ├── res_partner_view_inherit.xml   # Partner form/list extension (Client field)
│   ├── master_data_views.xml          # City and Skill master views + menus
│   ├── pipeline_summary_views.xml     # Pipeline Summary list, pivot, wizard, menus
│   ├── applicant_tracker_views.xml    # Applicant Tracker list, wizard, menus
│   └── assessment_report_views.xml    # Assessment Report list, wizard, menus
├── report/
│   ├── pipeline_summary_template.xml  # QWeb HTML/PDF report template (A3 Landscape)
│   └── pipeline_summary_report.xml    # Report action definition
├── migrations/
│   └── 19.0.2.1.{0–16}/              # Sequential pre/post migration scripts
├── security/
│   └── ir.model.access.csv            # Access rights for all custom models
└── static/src/img/
    └── linkedin_logo.png              # Custom LinkedIn button icon
```

---

## Installation

1. Copy the `recruitment_pipeline_report` folder into your Odoo addons directory.
2. Restart the Odoo server.
3. Go to Apps, search for "Recruitment Pipeline Summary Report", and click **Install**.
4. Required dependencies (`hr`, `hr_recruitment`, `hr_skills`) will be installed automatically if not already present.

---

## Configuration After Install

1. **Set up Cities** — Go to Recruitment → Configuration → Master Data → Cities and add the cities your organisation operates in.
2. **Set up Skills** — Go to Recruitment → Configuration → Master Data → Skills and add relevant skill names.
3. **Configure Job Positions** — Open each Job Position and fill in: Req ID, Employment Type, POC, Role Status, Experience Range, Locations, Skills, Recruiters, and Budget/Bill Rate.
4. **Link POC Contacts** — Open the relevant contact in Contacts, and set the "Client" field to link them to a Department for proper POC filtering on Job Positions.

---

## Notes

- `x_rec_id` is a deprecated alias for `x_req_id` kept for backward compatibility and can be removed in a future version.
- The Pipeline Summary view only includes applicants who have both a Job Position and a Department (Client) assigned.
- The Applicant Tracker and Assessment Report show both active and archived applicants (`active_test: False`).
- All Excel exports are generated using `xlsxwriter` and stored as temporary `ir.attachment` records before being served as downloads.