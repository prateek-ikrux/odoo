# -*- coding: utf-8 -*-
{
    'name': 'CRM Consulting Customization',
    'version': '19.0.1.9.0',
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

Access is CRM's own: this module adds no roles and no record rules, and who
may see or do what is whatever the Sales privilege already says.
""",
    'depends': ['crm', 'contacts', 'sales_team', 'mail'],
    'data': [
        'data/crm_stage_data.xml',
        'data/crm_lost_reason_data.xml',
        'views/crm_lead_views.xml',
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
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
