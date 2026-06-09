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
    'Client Round Slot Shared',
    'Client Round Scheduled',
    'Client Round Feedback Pending',
    'Client Round Reject',
    'TBO',
    'Offered/Yet to Join',
    'Joined',
    'Declined',
]

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
    'cr_slot_shared',
    'cr_scheduled',
    'cr_feedback_pending',
    'cr_reject',
    'tbo',
    'offered',
    'joined',
    'declined',
]

# Exact hr.recruitment.stage names as configured in the database (en_US).
STAGE_BY_FIELD = {
    'profiles_shared':        'Profile Shared',
    'screening_pending':      'Screening Pending',
    'duplicate_profiles':     'Duplicate Profiles',
    'assessment_link_shared':  'Assessment Link Shared',
    'assessment_reject':      'Assessment Reject',
    'l1_tbs':                 'L1 TBS',
    'l1_slot_shared':         'L1 Slot Shared',
    'l1_scheduled':           'L1 Scheduled',
    'l1_feedback_pending':    'L1 Feedback Pending',
    'l1_reject':              'L1 Reject',
    'l2_tbs':                 'L2 TBS',
    'l2_slot_shared':         'L2 Slot Shared',
    'l2_scheduled':           'L2 Scheduled',
    'l2_feedback_pending':    'L2 Feedback Pending',
    'l2_reject':              'L2 Reject',
    'cr_tbs':                 'Client Round TBS',
    'cr_slot_shared':         'Client Round Slot Shared',
    'cr_scheduled':           'Client Round Scheduled',
    'cr_feedback_pending':    'Client Round Feedback Pending',
    'cr_reject':              'Client Round Reject',
    'tbo':                    'TBO',
    'offered':                'Offered/Yet to Join',
    'joined':                 'Joined',
    'declined':               'Declined',
}

ALL_STAGE_NAMES = list(STAGE_BY_FIELD.values())

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
