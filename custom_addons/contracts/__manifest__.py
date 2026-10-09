# -*- coding: utf-8 -*-
{
    'name': 'Contracts',
    'version': '19.0.1.11.0',
    'category': 'Services/Contracts',
    'author': 'iKrux',
    'website': 'https://www.ikrux.com',
    'summary': 'Track client contracts through Active / Expired / Terminated states with Excel reporting',
    'description': """
Contracts
=========

Two sections of contract, sharing one lifecycle:

* The overarching contract agreeing that the client and we will work together
  for a period.
* The contract placed under it, agreeing that a named candidate will work for
  the client on our payroll.

Every contract moves through three states:

* Active - ongoing.
* Expired - the end date has passed; flipped automatically by a nightly scheduled action.
* Terminated - closed midway; set manually.

A contract records the client, the point of contact, who created it (read
only), the start and end dates, the number of days left, and at least one
mandatory document. An overarching contract also has a contract type, picked
from a master list kept under Contracts > Configuration > Contract Types. A
placed contract has no type; it additionally names the candidate and the role,
must reference the contract it sits under - one whose type allows Statements of
Work, such as Consulting - takes its client from that contract, and has to run
inside its period.

Before a contract runs out, a nightly scheduled action emails an internal list
at a set of day milestones - 45, 30 and 7 days left by default. Both the
milestones and the recipients are set under Contracts > Configuration >
Settings, so the schedule can be changed without a deploy, and the same screen
switches the reminders off altogether. Recipients start out empty, so nothing
is sent until they are filled in. Every reminder is logged in the contract's chatter, and extending an end
date starts the sequence over.

An overarching contract can instead run Until Completion of Service - for as
long as there is work under it. It then has no end date at all: it never
expires, shows no days left and sends no reminders, and the contracts placed
under it are bound only by its start date. A placed contract always has an
end date.

A contract that is extended records an Extended End Date. From then on it,
not the original end date, is what the contract runs to - expiry, days left
and the reminders all follow it, and extending re-arms the reminder sequence.
A placed contract also carries the next annual appraisal date, taken from the
start date, and free-text remarks.

Each section exports its own filtered Excel report.
""",
    'depends': ['base', 'base_setup', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'data/contract_type_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        # the wizard action is referenced by a button in the contract list view,
        # so it has to be loaded first
        'views/contract_report_wizard_views.xml',
        'views/contract_terminate_wizard_views.xml',
        'views/contract_type_views.xml',
        'views/contract_views.xml',
        # the settings action is referenced by the Configuration menu,
        # so it has to be loaded first
        'views/res_config_settings_views.xml',
        'views/contract_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'contracts/static/src/js/contracts_date_field.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
