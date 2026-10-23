# -*- coding: utf-8 -*-
{
    'name': 'CRM Consulting Customization',
    'version': '19.0.1.29.0',
    'category': 'Sales/CRM',
    'author': 'iKrux',
    'website': 'https://www.ikrux.com',
    'summary': 'Recruitment and consulting pipeline on top of CRM - four stages, '
               'engagement commercials and POC contacts',
    'description': """
CRM Consulting Customization
============================

Reshapes the CRM pipeline around a recruitment and consulting business.

The pipeline runs through four stages - New, Initial Outreach, Follow-up in
Progress and Agreement / MSA Signed. The stages are seeded once and are then
the Admin's to rename, reorder, add to or delete from the UI; nothing in this
module reads a stage by name or by external id, so none of that can break a
view or a filter. Where stage meaning is genuinely needed, the module reads
CRM's own "Is Won Stage?" flag.

An opportunity carries the commercial terms of the engagement. Every
engagement type agrees a Commercial Agreement; only the unit changes. An FTE
engagement is agreed as a percentage, a Consulting engagement in rupee lakhs
per month, and a blended FTE/Consulting engagement takes whichever of the two
the deal was struck on.

Closed-lost is a status carrying a mandatory reason, not a stage, so a lost
opportunity keeps the stage it died in and the reason is reportable on its own.

Several people work one account, so an opportunity names one owner and any
number of BDAs, and the form asks for the BDAs rather than a salesperson.

A client should have one opportunity per engagement type, but nothing is
refused. Saving an opportunity with a client name or engagement type new to
it pops up what CRM already holds for that client - read past case, spacing,
punctuation and a legal form such as Pvt Ltd - or a like-named one, other
BDAs' included, and the user saves anyway or discards the changes. Lost
opportunities do not count, and FTE/Consulting is a type of its own. Imports
have no popup; the Possible Duplicates filter finds what they bring in.

POCs are recorded on the opportunity itself, in one list with no limit on
how many, added a row at a time and dragged into order. The first is the
primary contact, whose details the opportunity keeps a copy of for Send
Email, Send SMS, the pipeline card and the lists.

Opportunities can email people as they move. Each kind is switched on and
configured under CRM > Configuration > Settings. Change notifications and
activity reminders follow one three-level hierarchy: Leadership, picked in
the settings; managers, who are the Team Leaders of sales teams; and BDAs,
the members of their teams.

* Change notifications - when an opportunity is created, deleted, or a change
  to it - its POC list included - is recorded in its audit log. Always to the
  opportunity's BDAs, those just taken off it among them; then a BDA's change
  to their team leader and leadership, a manager's to the BDAs' team leaders
  and leadership, and leadership's to the BDAs' team leaders. Never to the
  person themselves. Automatic changes go to the opportunity's whole
  hierarchy. Odoo's own "You have been assigned" email is left out for
  opportunities while these are on, as the change notification covers it.
* Stage Ageing Report - an email on the schedule picked - daily, weekly on
  a weekday, or monthly on a day of the month, at a time of day (weekly on
  Monday at midnight by default) - with an Excel list of every active client
  whose opportunity has not progressed beyond its current stage for the days
  picked or more (6 by default).
* Client Inactivity Report - the same, for every active client whose
  opportunity has had no recorded activity for the days picked or more (7 by
  default). Activity is any edit to the opportunity, a note, message or
  email in its chatter - a client's reply included - or an activity
  scheduled, rescheduled or completed on it; automatic changes do not count.
  When it last happened is the opportunity's Last Activity, in the list.

  Each report has its own schedule and its own list. In each, every stage
  says whether it is included, the won stage starting left out, and the report goes to its own list, nobody by default,
  which Select everyone and Clear fill or empty in one click.
* Activity reminders - a set number of days before a scheduled activity of
  the picked types falls due (3 and 1 days, Call and Meeting by default), to
  the person it is assigned to and, each behind a tick that starts on, their
  sales team leader and leadership above them.
* Tagged colleagues - anyone tagged with @ in an opportunity's chatter gets
  an email saying who tagged them on which opportunity, with the message and
  a button into it, in place of Odoo's bare one. The message stays in their
  Inbox too.

Access is CRM's own Sales privilege, with one widening: a salesperson on
"Own documents only" sees every opportunity they are a BDA on, not only those
they are the Primary BDA of. This module adds no roles, and only Sales users
can be picked as BDAs.
""",
    'depends': ['crm', 'contacts', 'sales_team', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/crm_lead_security.xml',
        'security/crm_lead_poc_security.xml',
        'data/crm_stage_data.xml',
        'data/crm_classification_data.xml',
        'data/crm_lost_reason_data.xml',
        'data/crm_reminder_day_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/crm_lead_views.xml',
        'views/crm_stage_views.xml',
        'views/res_config_settings_views.xml',
        'views/crm_classification_views.xml',
        'views/res_partner_views.xml',
        'wizard/crm_poc_export_wizard_views.xml',
    ],
    # ordinal_date, the "21st July 2024" date widget. Neither strftime nor
    # Luxon can express an ordinal suffix, so the string is built in the
    # browser rather than configured on the language.
    'assets': {
        'web.assets_backend': [
            'crm_consulting_customization/static/src/ordinal_date_field.js',
            'crm_consulting_customization/static/src/client_duplicate_check.js',
        ],
    },
    # Fills the BDA list of opportunities that predate this module, which
    # would otherwise be left with an owner who is not one of their own BDAs.
    # Also leaves the won stage out of both pipeline reports, dates every
    # opportunity's last activity from its history, and picks
    # the default activity types for activity reminders.
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
