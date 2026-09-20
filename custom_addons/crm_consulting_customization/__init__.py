# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Put the owner of every pre-existing opportunity into its BDA list.

    Opportunities that predate this module have no BDA - the column did not
    exist when they were written - which leaves them contradicting the rule
    the rest of the module relies on, that the owner is always one of the
    BDAs. Until they are repaired, a BDA cannot find their own older
    opportunities by the BDA half of the record rule, reports grouped by BDA
    file them under "None", and the first edit to one is refused for a field
    nobody touched.

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
