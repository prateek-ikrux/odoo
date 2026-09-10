# -*- coding: utf-8 -*-
{
    'name': 'Recruitment Pipeline Summary Report',
    'version': '19.0.2.1.36',
    'category': 'Recruitment',
    'author': 'iKrux',
    'summary': 'Pipeline Summary pivot + Excel report with full stage tracking, Applicant Tracker, and Internal Assessment Report',
    'depends': ['hr', 'hr_recruitment', 'hr_skills', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/utm_source_data.xml',
        'views/res_partner_view_inherit.xml',
        'views/hr_department_view_inherit.xml',
        'views/master_data_views.xml',
        'views/recruiter_team_views.xml',
        'views/hr_job_view_inherit.xml',
        'views/hr_applicant_view_inherit.xml',
        'report/pipeline_summary_template.xml',
        'report/pipeline_summary_report.xml',
        'views/pipeline_summary_views.xml',
        'views/applicant_tracker_views.xml',
        'views/assessment_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Tabler Icons (CDN) — loaded before our component
            ('include', 'https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css'),
            'recruitment_pipeline_report/static/src/scss/help_center.scss',
            'recruitment_pipeline_report/static/src/xml/help_center.xml',
            'recruitment_pipeline_report/static/src/js/help_center.js',
            'recruitment_pipeline_report/static/src/scss/hr_job_kanban.scss',
            'recruitment_pipeline_report/static/src/js/hr_job_kanban_role_status.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
