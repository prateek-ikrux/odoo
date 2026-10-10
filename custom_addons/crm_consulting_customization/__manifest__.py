# -*- coding: utf-8 -*-
{
    'name': 'CRM Consulting Customization',
    'version': '19.0.1.21.0',
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

Up to five POCs are recorded on the opportunity itself. The first is shown
and each further one is asked for, so the form starts at one contact and
walks out to five.

Opportunities can email people as they move. Each kind is switched on and
configured under CRM > Configuration > Settings, and every one goes to the
opportunity's own BDAs plus anyone picked there:

* Change notifications - when an opportunity is created, deleted, or a change
  to it is recorded in its audit log.
* Stuck-in-stage reminders - when an active client's opportunity stays in one
  stage past the day marks picked (6, 12, 18 and 30 by default). Each stage
  says whether it sends them; the won stage starts switched off.
* Activity reminders - a set number of days before a scheduled activity of
  the picked types falls due (3 and 1 days, Call and Meeting by default),
  also to the person it is assigned to.

Access is CRM's own: this module adds no roles and no record rules, and who
may see or do what is whatever the Sales privilege already says.
""",
    'depends': ['crm', 'contacts', 'sales_team', 'mail'],
    'data': [
        'security/ir.model.access.csv',
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
    ],
    # ordinal_date, the "21st July 2024" date widget. Neither strftime nor
    # Luxon can express an ordinal suffix, so the string is built in the
    # browser rather than configured on the language.
    'assets': {
        'web.assets_backend': [
            'crm_consulting_customization/static/src/ordinal_date_field.js',
        ],
    },
    # Fills the BDA list of opportunities that predate this module, which
    # would otherwise be left with an owner who is not one of their own BDAs.
    # Also switches off stuck-in-stage reminders on the won stage and picks
    # the default activity types for activity reminders.
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
