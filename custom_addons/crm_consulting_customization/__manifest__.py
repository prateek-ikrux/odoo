# -*- coding: utf-8 -*-
{
    'name': 'CRM Consulting Customization',
    'version': '19.0.1.4.0',
    'category': 'Sales/CRM',
    'author': 'iKrux',
    'website': 'https://www.ikrux.com',
    'summary': 'Recruitment and consulting pipeline on top of CRM - four stages, '
               'engagement commercials, POC contacts and role-based access',
    'description': """
CRM Consulting Customization
============================

Reshapes the CRM pipeline around a recruitment and consulting business.

The pipeline runs through four stages - New, Initial Outreach, Follow-up in
Progress and Agreement / MSA Signed. The stages are seeded once and are then
the Admin's to rename, reorder, add to or delete from the UI; nothing in this
module reads a stage by name or by external id, so none of that can break a
view, a filter or a report. Where stage meaning is genuinely needed, the
module reads CRM's own "Is Won Stage?" flag.

An opportunity carries the commercial terms of the engagement. Every
engagement type agrees a Commercial Agreement; only the unit changes. An FTE
engagement is agreed as a percentage, a Consulting engagement in rupee lakhs
per month, and a blended FTE/Consulting engagement takes whichever of the two
the deal was struck on.

Closed-lost is a status carrying a mandatory reason, not a stage, so a lost
opportunity keeps the stage it died in and the reason is reportable on its own.

Several people work one account, so an opportunity names one owner and any
number of BDAs. Reports grouped by BDA attribute the opportunity to each of
them.

Up to five POCs are recorded on the opportunity itself. The first is shown
and each further one is asked for, so the form starts at one contact and
walks out to five.

Four roles - BDA, Sales / Sales Head, Leadership and Admin - divide the
pipeline. A BDA works only the opportunities they own. Nobody below Admin can
delete anything; records are archived or marked lost instead.
""",
    'depends': ['crm', 'contacts', 'sales_team', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/crm_stage_data.xml',
        'data/crm_lost_reason_data.xml',
        'data/ir_cron_data.xml',
        'views/crm_lead_views.xml',
        'views/res_partner_views.xml',
        'report/crm_lead_report_views.xml',
    ],
    # Fills the BDA list of opportunities that predate this module, which
    # would otherwise be left with an owner who is not one of their own BDAs.
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
