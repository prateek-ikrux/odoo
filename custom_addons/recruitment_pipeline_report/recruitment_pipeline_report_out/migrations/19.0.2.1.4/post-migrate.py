# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def migrate(cr, version):
    """Map backed-up internal user POCs to res.partner contacts."""
    if not _column_exists(cr, 'hr_job', 'x_poc_user_id_backup'):
        return

    cr.execute("""
        SELECT j.id, j.department_id, u.partner_id
        FROM hr_job j
        JOIN res_users u ON u.id = j.x_poc_user_id_backup
        WHERE j.x_poc_user_id_backup IS NOT NULL
          AND u.partner_id IS NOT NULL
    """)
    rows = cr.fetchall()
    migrated = 0

    for job_id, dept_id, partner_id in rows:
        if dept_id and _column_exists(cr, 'res_partner', 'x_client_department_id'):
            cr.execute("""
                UPDATE res_partner
                SET x_client_department_id = %s
                WHERE id = %s AND x_client_department_id IS NULL
            """, (dept_id, partner_id))
        cr.execute("UPDATE hr_job SET x_poc_id = %s WHERE id = %s", (partner_id, job_id))
        migrated += 1

    if _column_exists(cr, 'hr_applicant', 'x_poc_id'):
        cr.execute("""
            UPDATE hr_applicant a
            SET x_poc_id = j.x_poc_id
            FROM hr_job j
            WHERE a.job_id = j.id
        """)

    cr.execute("ALTER TABLE hr_job DROP COLUMN IF EXISTS x_poc_user_id_backup")
    _logger.info('Migrated %s job POC references to res.partner contacts.', migrated)
