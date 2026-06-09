# -*- coding: utf-8 -*-
import io
import json

from werkzeug.datastructures import FileStorage

from odoo import http
from odoo.http import content_disposition, request
from odoo.addons.web.controllers.pivot import TableExporter
from odoo.tools import osutil


class PipelinePivotExport(TableExporter):

    @http.route('/web/pivot/export_xlsx', type='http', auth='user', readonly=True)
    def export_xlsx(self, data, **kw):
        jdata = json.load(data) if isinstance(data, FileStorage) else json.loads(data)
        if jdata.get('model') == 'recruitment.pipeline.summary.view':
            return self._export_pipeline_summary_xlsx()
        return super().export_xlsx(data, **kw)

    def _export_pipeline_summary_xlsx(self):
        xlsx_data = request.env['recruitment.pipeline.summary.view']._generate_xlsx_bytes()
        filename = osutil.clean_filename('Pipeline Summary')
        return request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename + '.xlsx')),
            ],
        )
