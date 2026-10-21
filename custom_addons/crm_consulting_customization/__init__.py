# -*- coding: utf-8 -*-
from . import models
from . import wizard
from .models.crm_lead import fill_last_activity_dates


def post_init_hook(env):
    """Put the owner of every pre-existing opportunity into its BDA list.

    Opportunities that predate this module have no BDA - the column did not
    exist when they were written - which leaves them contradicting the rule
    the rest of the module relies on, that the owner is always one of the
    BDAs. Until they are repaired, an older opportunity files under no BDA at
    all, and the first edit to one is refused for a field nobody touched.

    Only the owner is filled in; anyone else who worked the account has to be
    added by hand, because nothing in the database records who that was.
    Opportunities with no owner at all are left alone - there is nobody to
    put in - and the form asks for a BDA the next time one is saved.
    """
    leads = env['crm.lead'].with_context(active_test=False).search([
        ('user_id', '!=', False),
        ('bda_ids', '=', False),
    ])
    for lead in leads:
        lead.bda_ids = [(4, lead.user_id.id)]
    setup_notification_defaults(env)
    # The column arrived dated today on every opportunity; date it from each
    # one's own history instead.
    fill_last_activity_dates(env.cr)


def setup_notification_defaults(env):
    """Starting values for the email notifications, set once.

    The won stage is where a deal is meant to rest, so it is left out of the
    Stage Ageing and Client Inactivity reports until someone ticks it. Activity reminders start
    out covering calls and meetings, and going up the hierarchy to the
    assignee's team leader and leadership. All are the Admin's to change
    after.
    """
    env['crm.stage'].search([('is_won', '=', True)]).write({
        'stage_reminders': False,
        'inactivity_reminders': False,
    })
    types = env['mail.activity.type']
    for xmlid in ('mail.mail_activity_data_call', 'mail.mail_activity_data_meeting'):
        types |= env.ref(xmlid, raise_if_not_found=False) or types
    for company in env['res.company'].search([]):
        if not company.crm_activity_reminder_type_ids:
            company.crm_activity_reminder_type_ids = types
    params = env['ir.config_parameter'].sudo()
    for key in ('crm_consulting.activity_reminders_team_leader',
                'crm_consulting.activity_reminders_leadership'):
        if params._get_param(key) is None:
            params.set_param(key, True)
