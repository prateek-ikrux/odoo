# -*- coding: utf-8 -*-
"""Shared column definitions for Pipeline Summary (PDF, Excel, list)."""

PRIMARY_HEADERS = [
    '#', 'Client', 'POC', 'Role', 'Role Type', 'Role Status', 'Role Status Remarks', 'No. of positions',
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
EMP_TYPE_LABELS     = {'fte': 'FTE', 'consulting': 'Consulting'}
