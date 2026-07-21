# -*- coding: utf-8 -*-
"""Shared column definitions for Pipeline Summary (PDF, Excel, list)."""

from datetime import datetime, time
import pytz

PRIMARY_HEADERS = [
    '#', 'Client', 'POC', 'Role', 'Role Type', 'Role Status', 'Role Status Remarks',
    'Role Received from Client', 'Role Opened to Team', 'No. of positions',
]


ROLE_STATUS_SELECTION = [
    ('active',      'Active'),
    ('in_progress', 'In Progress'),
    ('on_hold',     'On Hold'),
    ('closed',      'Closed'),
]

SUB_STATUS_SELECTION = [
    ('candidate_drop',      'Candidate Drop'),
    ('drop_by_client',      'Drop by Client'),
    ('on_hold_alignment',   'On Hold Due to Alignment'),
    ('nil',                 'N/A'),
]

ROLE_STATUS_LABELS  = dict(ROLE_STATUS_SELECTION)
SUB_STATUS_LABELS   = dict(SUB_STATUS_SELECTION)
EMP_TYPE_LABELS     = {'fte': 'FTE', 'consulting': 'Consulting', 'fte_consulting': 'FTE/Consulting'}

# Which timestamp a report's Date Range filters against.
# - create_date: when the candidate profile was added to the system (legacy behaviour).
# - date_last_stage_update: includes candidates whose stage changed during the range.
#   In Pipeline Summary this scans the full stage-change history (see
#   stage_history.py) and shows each candidate's stage as it stood at the end of
#   the range. Applicant Tracker and Assessment Report instead filter on the
#   native hr.applicant.date_last_stage_update field (only the single most
#   recent change), which is simpler but misses a candidate whose latest move
#   landed just outside the chosen range.
DATE_FILTER_TYPE_SELECTION = [
    ('create_date',             'Profile Created Date'),
    ('date_last_stage_update',  'Last Stage Activity Date'),
]


def build_date_range_domain(env, date_from, date_to, field_name='create_date'):
    """Build a timezone-aware datetime range domain for a Date/Datetime field.

    date_from/date_to are plain dates picked by the user in their own timezone.
    They must be converted to UTC datetime bounds using that timezone, or the
    day boundary is wrong for every user not on UTC (naive 'YYYY-MM-DD 00:00:00'
    strings are interpreted as UTC, not the user's local midnight).
    """
    domain = []
    if not (date_from or date_to):
        return domain
    tz = pytz.timezone(env.user.tz or 'UTC')
    if date_from:
        start = tz.localize(datetime.combine(date_from, time.min))
        domain.append((field_name, '>=', start.astimezone(pytz.utc).replace(tzinfo=None)))
    if date_to:
        end = tz.localize(datetime.combine(date_to, time.max))
        domain.append((field_name, '<=', end.astimezone(pytz.utc).replace(tzinfo=None)))
    return domain
