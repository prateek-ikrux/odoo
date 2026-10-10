# -*- coding: utf-8 -*-
from . import models

# Stages a candidate is meant to stay in once they get there. They start with
# stuck-candidate reminders switched off; any stage can be changed later
# under Recruitment > Configuration > Stages.
OUTCOME_STAGE_NAMES = (
    'Duplicate Profile', 'L1 Reject', 'L2 Reject', 'L3 Reject',
    'Joined', 'Declined', 'Quit Post Joining',
)


def post_init_hook(env):
    setup_notification_defaults(env)


def setup_notification_defaults(env):
    """Starting state for the stuck-candidate reminders, set once.

    Outcome stages - and whichever stage is the hired one - send no stuck
    reminders. Every candidate's Entered Stage On is taken from the last
    stage change in their history, falling back to when they were added, so
    nobody already in the pipeline looks as if they had just moved.
    """
    Stage = env['hr.recruitment.stage'].with_context(active_test=False)
    Stage.search(['|', ('hired_stage', '=', True), ('name', 'in', OUTCOME_STAGE_NAMES)]) \
        .write({'x_stage_reminders': False})
    env.cr.execute("""
        UPDATE hr_applicant a
           SET x_stage_entered_date = COALESCE((
                   SELECT max(m.date)
                     FROM mail_message m
                     JOIN mail_tracking_value t ON t.mail_message_id = m.id
                     JOIN ir_model_fields f ON f.id = t.field_id
                    WHERE m.model = 'hr.applicant' AND m.res_id = a.id
                      AND f.model = 'hr.applicant' AND f.name = 'stage_id'
               ), a.create_date)
    """)
    env['hr.applicant'].invalidate_model(['x_stage_entered_date'])
