# -*- coding: utf-8 -*-
{
    'name': 'CRM Meeting Reminders',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'author': 'iKrux',
    'website': 'https://www.ikrux.com',
    'summary': 'Timed email reminders before a meeting linked to an opportunity',
    'description': """
CRM Meeting Reminders
=====================

Emails a reminder ahead of every meeting that is linked to an opportunity, at a
set of hour milestones - 48, 24, 12 and 1 hour before by default. Meetings with
no opportunity behind them are left alone, as are Odoo's own per-meeting
reminders, which keep working independently.

One mail goes out per meeting per milestone: the attendees who have not declined
are on it, and a standing list of addresses is copied in regardless of whether
they are involved. The sending address is set here too, so it can be made to
match what the outgoing mail server is allowed to send as, with replies still
going back to the organiser.

Everything is configured under CRM > Configuration > Settings: the milestones,
the standing recipients, the sending address, and an overall on/off switch.
Rescheduling a meeting starts its reminder sequence over.
""",
    'depends': ['crm', 'calendar', 'mail', 'base_setup'],
    'data': [
        'data/ir_config_parameter_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
