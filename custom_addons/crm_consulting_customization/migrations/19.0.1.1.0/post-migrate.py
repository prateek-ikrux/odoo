# -*- coding: utf-8 -*-
"""Backfill the BDA list of opportunities that predate the bda_ids field.

The same repair the post-install hook performs, for databases where this
module was installed before that hook existed. Both call the one
implementation so the two paths cannot drift apart.
"""
import logging

from odoo import SUPERUSER_ID, api
from odoo.addons.crm_consulting_customization import post_init_hook

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    post_init_hook(env)
    _logger.info("crm_consulting_customization: BDA lists backfilled from the owner")
