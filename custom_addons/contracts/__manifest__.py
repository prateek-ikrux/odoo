# -*- coding: utf-8 -*-
{
    'name': 'Contracts',
    'version': '19.0.1.2.0',
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

A contract records the client, the point of contact, who created it (read only),
the start and end dates, the number of days left, and at least one mandatory
document. A placed contract additionally names the candidate and the role, must
reference the contract it sits under, takes its client from that contract, and
has to run inside its period.

Before a contract runs out, a nightly scheduled action emails an internal list
at a set of day milestones - 45, 30 and 7 days left by default. Both the
milestones and the recipients are system parameters, 'contracts.reminder_days'
and 'contracts.reminder_emails', so the schedule can be changed without a
deploy. Recipients start out empty, so nothing is sent until they are filled
in. Every reminder is logged in the contract's chatter, and extending an end
date starts the sequence over.

Each section exports its own filtered Excel report.
""",
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        # the wizard action is referenced by a button in the contract list view,
        # so it has to be loaded first
        'views/contract_report_wizard_views.xml',
        'views/contract_terminate_wizard_views.xml',
        'views/contract_views.xml',
        'views/contract_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
