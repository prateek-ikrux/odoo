# -*- coding: utf-8 -*-
"""Migration 19.0.2.1.37

Rename the fixed Source from "iKrux Engineering" to "Shenzyn". Runs as a
pre-migrate so the xmlid rename (utm_source_ikrux_engineering ->
utm_source_shenzyn) happens before this module's data files are reloaded
during the upgrade - data/utm_source_data.xml now declares id
"utm_source_shenzyn", and without this rename the noupdate="1" record
loader wouldn't recognize it as the existing record, creating a duplicate
utm.source instead of reusing the one already referenced by existing
applicants.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        SELECT res_id FROM ir_model_data
        WHERE module = 'recruitment_pipeline_report'
          AND name = 'utm_source_ikrux_engineering'
          AND model = 'utm.source'
    """)
    row = cr.fetchone()
    if not row:
        _logger.warning(
            'Could not find the old "iKrux Engineering" utm.source xmlid; '
            'nothing to rename.'
        )
        return

    source_id = row[0]

    cr.execute("""
        UPDATE ir_model_data
        SET name = 'utm_source_shenzyn'
        WHERE module = 'recruitment_pipeline_report'
          AND name = 'utm_source_ikrux_engineering'
          AND model = 'utm.source'
    """)

    cr.execute("""
        UPDATE utm_source
        SET name = 'Shenzyn'
        WHERE id = %s
    """, (source_id,))

    _logger.info(
        'Renamed utm.source #%s from "iKrux Engineering" to "Shenzyn" '
        '(xmlid utm_source_ikrux_engineering -> utm_source_shenzyn).',
        source_id,
    )
