# -*- coding: utf-8 -*-
"""Reconstructs each hr.applicant's recruitment stage as of a past moment
in time.

hr_recruitment already marks `hr.applicant.stage_id` as tracking=True, so
every stage change - past and future - is already logged in that record's
chatter (mail.message + mail.tracking.value), with the date it happened.
This module reads that existing log; it needs no new field, no migration,
and no backfill.
"""
from datetime import datetime, time

import pytz

from odoo import fields


def as_of_utc_datetime(env, date_value):
    """Convert a plain date (picked by the user in their own timezone) into
    the UTC datetime representing the end of that day in the user's tz -
    i.e. the latest moment considered part of that calendar day.

    Falls back to "now" when no date is given, so an empty as-of date
    behaves as "as of right now" rather than raising or matching nothing.
    """
    if not date_value:
        return fields.Datetime.now()
    tz = pytz.timezone(env.user.tz or 'UTC')
    end_of_day = tz.localize(datetime.combine(date_value, time.max))
    return end_of_day.astimezone(pytz.utc).replace(tzinfo=None)


def day_start_utc(env, date_value):
    """Convert a plain date into the UTC datetime for the start of that day
    in the user's timezone - the lower-bound counterpart to
    as_of_utc_datetime's end-of-day upper bound.

    Returns None when no date is given (an open-ended lower bound), unlike
    as_of_utc_datetime which falls back to "now" - the two functions serve
    different roles (a required as-of cutoff vs. an optional range start).
    """
    if not date_value:
        return None
    tz = pytz.timezone(env.user.tz or 'UTC')
    start_of_day = tz.localize(datetime.combine(date_value, time.min))
    return start_of_day.astimezone(pytz.utc).replace(tzinfo=None)


def get_applicants_moved_between(env, start_datetime, end_datetime, applicant_ids=None):
    """Return the set of applicant ids that had at least one tracked
    stage_id change timestamped between start_datetime and end_datetime
    (inclusive; start_datetime may be None for an open-ended lower bound).

    Unlike hr.applicant's native date_last_stage_update, which only ever
    remembers the single most recent stage change, this scans the full
    history - so a candidate who moved twice, with only their *later* move
    landing outside the window, is still correctly included.
    """
    if applicant_ids is not None and not applicant_ids:
        return set()

    params = {'end': end_datetime}
    applicant_filter = ''
    if applicant_ids:
        applicant_filter = 'AND mm.res_id IN %(applicant_ids)s'
        params['applicant_ids'] = tuple(applicant_ids)

    start_clause = ''
    if start_datetime:
        start_clause = 'AND mm.create_date >= %(start)s'
        params['start'] = start_datetime

    query = f"""
        SELECT DISTINCT mm.res_id
        FROM mail_tracking_value mtv
        JOIN mail_message mm      ON mm.id = mtv.mail_message_id
        JOIN ir_model_fields f    ON f.id = mtv.field_id
        WHERE mm.model = 'hr.applicant'
          AND f.model  = 'hr.applicant'
          AND f.name   = 'stage_id'
          AND mm.create_date <= %(end)s
          {start_clause}
          {applicant_filter}
    """
    env.cr.execute(query, params)
    return {row[0] for row in env.cr.fetchall()}


def get_stage_as_of(env, as_of_datetime, applicant_ids=None):
    """Return {applicant_id: stage_id} reflecting each applicant's
    recruitment stage as of `as_of_datetime` (a naive UTC datetime).

    Applicants created after `as_of_datetime` didn't exist yet at that
    moment and are omitted from the result. An applicant that never had a
    tracked stage change keeps its current stage_id (nothing to reconstruct
    - it has always been in that stage).

    `applicant_ids`, when given, scopes the whole query (including the
    history scan itself) to just those candidates - this is normally called
    with the small set already matched by a wizard's other filters, not the
    whole table. Pass None (the default) to compute it for every applicant.
    An explicitly empty list returns {} without querying, since there is
    nothing to look up and the history scan is the expensive part.
    """
    if applicant_ids is not None and not applicant_ids:
        return {}

    params = {'as_of': as_of_datetime}
    events_filter = ''
    applicant_filter = ''
    if applicant_ids:
        events_filter = 'AND mm.res_id IN %(applicant_ids)s'
        applicant_filter = 'AND a.id IN %(applicant_ids)s'
        params['applicant_ids'] = tuple(applicant_ids)

    query = f"""
        WITH events AS (
            SELECT mm.res_id            AS applicant_id,
                   mm.create_date       AS change_date,
                   mm.id                AS message_id,
                   mtv.old_value_integer AS old_stage_id,
                   mtv.new_value_integer AS new_stage_id
            FROM mail_tracking_value mtv
            JOIN mail_message mm      ON mm.id = mtv.mail_message_id
            JOIN ir_model_fields f    ON f.id = mtv.field_id
            WHERE mm.model = 'hr.applicant'
              AND f.model  = 'hr.applicant'
              AND f.name   = 'stage_id'
              {events_filter}
        ),
        last_on_or_before AS (
            SELECT DISTINCT ON (applicant_id) applicant_id, new_stage_id AS stage_id
            FROM events
            WHERE change_date <= %(as_of)s
            ORDER BY applicant_id, change_date DESC, message_id DESC
        ),
        first_after AS (
            SELECT DISTINCT ON (applicant_id) applicant_id, old_stage_id AS stage_id
            FROM events
            WHERE change_date > %(as_of)s
            ORDER BY applicant_id, change_date ASC, message_id ASC
        )
        SELECT a.id AS applicant_id,
               COALESCE(lob.stage_id, fa.stage_id, a.stage_id) AS stage_id_as_of
        FROM hr_applicant a
        LEFT JOIN last_on_or_before lob ON lob.applicant_id = a.id
        LEFT JOIN first_after fa        ON fa.applicant_id = a.id
        WHERE a.create_date <= %(as_of)s
        {applicant_filter}
    """
    env.cr.execute(query, params)
    return {applicant_id: stage_id for applicant_id, stage_id in env.cr.fetchall()}
