# -*- coding: utf-8 -*-
"""Shared column definitions for Pipeline Summary (PDF, Excel, list)."""

PRIMARY_HEADERS = [
    '#', 'Client', 'POC', 'Role', 'Role Type', 'Role Status', 'Sub Status', 'No. of positions',
]

SECONDARY_HEADERS = [
    'Profiles Shared',
    'Screening Pending',
    'Duplicate Profiles',
    'Assessment Link Shared',
    'Assessment Reject',
    'L1 TBS',
    'L1 Slot Shared',
    'L1 Scheduled',
    'L1 Feedback Pending',
    'L1 Reject',
    'L2 TBS',
    'L2 Slot Shared',
    'L2 Scheduled',
    'L2 Feedback Pending',
    'L2 Reject',
    'Client Round TBS',
    'Client Round Scheduled',
    'Client Round Feedback Pending',
    'Client Round Reject',
    'TBO',
    'Offered/Yet to Join',
    'Joined',
    'Declined',
]

# Field names on recruitment.pipeline.summary.view matching SECONDARY_HEADERS
MEASURE_FIELDS = [
    'profiles_shared',
    'screening_pending',
    'duplicate_profiles',
    'assessment_link_shared',
    'assessment_reject',
    'l1_tbs',
    'l1_slot_shared',
    'l1_scheduled',
    'l1_feedback_pending',
    'l1_reject',
    'l2_tbs',
    'l2_slot_shared',
    'l2_scheduled',
    'l2_feedback_pending',
    'l2_reject',
    'cr_tbs',
    'cr_scheduled',
    'cr_feedback_pending',
    'cr_reject',
    'tbo',
    'offered',
    'joined',
    'declined',
]

ROLE_STATUS_SELECTION = [
    ('active', 'Active'),
    ('in_progress', 'In Progress'),
    ('on_hold', 'On Hold'),
    ('closed', 'Closed'),
]

SUB_STATUS_SELECTION = [
    ('candidate_drop', 'Candidate Drop'),
    ('drop_by_client', 'Drop by Client'),
    ('on_hold_alignment', 'On Hold Due to Alignment'),
    ('nil', 'N/A'),
]

ROLE_STATUS_LABELS = dict(ROLE_STATUS_SELECTION)
SUB_STATUS_LABELS = dict(SUB_STATUS_SELECTION)
EMP_TYPE_LABELS = {'fte': 'FTE', 'consulting': 'Consulting'}
