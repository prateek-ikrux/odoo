# -*- coding: utf-8 -*-
{
    'name': 'Recruitment Pipeline Summary Report',
    'version': '19.0.2.1.8',
    'category': 'Recruitment',
    'summary': 'Pipeline Summary pivot + Excel report with full stage tracking, and Applicant Tracker Excel export',
    'depends': ['hr', 'hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_view_inherit.xml',
        'views/hr_department_view_inherit.xml',
        'views/hr_job_view_inherit.xml',
        'views/hr_applicant_view_inherit.xml',
        'report/pipeline_summary_template.xml',
        'report/pipeline_summary_report.xml',
        'views/pipeline_summary_views.xml',
        'views/applicant_tracker_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
