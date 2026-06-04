# -*- coding: utf-8 -*-
{
    'name': 'Recruitment Custom Report',
    'version': '19.0.1.0.3',
    'category': 'Recruitment',
    'summary': 'Custom PDF reports for the Recruitment module',
    'description': """
        Adds custom reports to the Recruitment module:
        - Recruitment Pipeline Summary (per job position & stage)
        - Stage-wise Applicant Analysis
        - Recruitment Activity Report (per recruiter)
        - Applicant Status Report (In Progress / Hired / Refused)

        Reports are available from Recruitment → Custom Reports (direct PDF)
        and from the Applicants list/form via the Print menu.
    """,
    'author': 'iKrux',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'hr_recruitment',
    ],
    'data': [
        'security/ir_model_access.xml',
        'report/recruitment_report_templates.xml',
        'report/recruitment_report_actions.xml',
        'views/recruitment_report_wizard_views.xml',
        'views/recruitment_report_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
