# -*- coding: utf-8 -*-
"""Migration 19.0.2.1.15

Changes:
  1. x_notice_period: no DB change needed — 'serving_notice' is a new
     Selection value; existing rows keep their current values unchanged.
  2. priority: the field is extended from 0–3 to 0–5. The column is VARCHAR
     in PostgreSQL so existing values ('0','1','2','3') remain valid.
     No data migration required.
  3. hr.job.create_action override: Python-only, no DB change.
"""
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('Pre-migration 19.0.2.1.15: no schema changes required.')
