# -*- coding: utf-8 -*-
import logging

from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    registry = Registry(cr.dbname)
    with registry.cursor() as new_cr:
        env = api.Environment(new_cr, SUPERUSER_ID, {})
        jobs = env['hr.job'].search([])
        jobs._compute_display_name_with_type()
        _logger.info('Recomputed job display labels for %s job positions.', len(jobs))
        new_cr.commit()
