# -*- coding: utf-8 -*-
import base64
import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def migrate(cr, version):
    """The dedicated x_cv_upload field (and its helper fields
    x_cv_upload_filename, x_cv_attachment_id) are being removed. CV uploads
    now go through the native chatter paperclip / ir.attachment flow only,
    like any other document on the applicant.

    x_cv_upload was attachment=False, so its bytes were stored inline as a
    plain column on hr_applicant rather than in ir.attachment. Once the
    field is removed, that column is dropped by the ORM and that data would
    be lost outright.

    Most applicants should already have an equivalent file via
    x_cv_attachment_id (created by the old _sync_cv_attachment() on every
    save) - those attachments already exist as normal ir.attachment rows
    and are untouched by this migration; removing the field does not
    remove them. This migration only handles the gap case: any applicant
    whose inline x_cv_upload bytes were never synced to an attachment, so
    that data is preserved as a normal ir.attachment instead of vanishing
    when the column is dropped.
    """
    if not _column_exists(cr, 'hr_applicant', 'x_cv_upload'):
        return

    has_attachment_link_column = _column_exists(cr, 'hr_applicant', 'x_cv_attachment_id')

    if has_attachment_link_column:
        cr.execute("""
            SELECT id, x_cv_upload, x_cv_upload_filename
            FROM hr_applicant
            WHERE x_cv_upload IS NOT NULL
              AND x_cv_attachment_id IS NULL
        """)
    else:
        cr.execute("""
            SELECT id, x_cv_upload, x_cv_upload_filename
            FROM hr_applicant
            WHERE x_cv_upload IS NOT NULL
        """)
    rows = cr.fetchall()

    if not rows:
        _logger.info(
            'No un-synced inline x_cv_upload data found; nothing to preserve '
            'before dropping the field.'
        )
        return

    preserved = 0
    for applicant_id, data, filename in rows:
        if isinstance(data, bytes):
            try:
                base64.b64decode(data, validate=True)
                b64_str = data.decode('ascii')
            except Exception:
                b64_str = base64.b64encode(data).decode('ascii')
        else:
            b64_str = data

        cr.execute("""
            INSERT INTO ir_attachment
                (name, datas, res_model, res_id, type, create_date, write_date)
            VALUES
                (%s, %s, 'hr.applicant', %s, 'binary', now(), now())
        """, (filename or 'CV_%s' % applicant_id, b64_str, applicant_id))
        preserved += 1

    _logger.info(
        'Preserved %s CV(s) as ir.attachment ahead of removing the x_cv_upload '
        'field; these now appear via the standard chatter paperclip / '
        'Documents app like any other attachment.',
        preserved,
    )
