# -*- coding: utf-8 -*-
{
    'name': 'Contracts',
    'version': '19.0.1.0.0',
    'category': 'Services/Contracts',
    'author': 'iKrux',
    'website': 'https://www.ikrux.com',
    'summary': 'Track client contracts through Active / Expired / Terminated states with Excel reporting',
    'description': """
Contracts
=========

Keep track of client contracts across three states:

* Active - ongoing contracts.
* Expired - the end date has passed; flipped automatically by a nightly scheduled action.
* Terminated - closed midway; set manually.

Each contract records the client, the role, who created it (read only), the start
and end dates, the number of days left, and at least one mandatory attachment.

A Reporting menu opens a wizard that exports the filtered contracts to Excel.
""",
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        # the wizard action is referenced by a button in the contract list view,
        # so it has to be loaded first
        'views/contract_report_wizard_views.xml',
        'views/contract_views.xml',
        'views/contract_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
