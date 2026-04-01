import base64
import io
import json
import uuid
from datetime import date, datetime, time

from markupsafe import Markup
from odoo import _, api, models
from odoo.addons.web.controllers.export import CSVExport
from odoo.tools.misc import xlsxwriter


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        if isinstance(obj, (bytes, bytearray, memoryview)):
            return base64.b64encode(bytes(obj)).decode()
        return super().default(obj)


class Base(models.AbstractModel):
    _inherit = "base"

    def _export_chunk_bg(self, data, export_id, export_format):
        """Export a chunk of records in background.
        This method processes a subset of records and creates an intermediate attachment.
        When all chunks are processed, combines them into the final export file.
        """
        params = json.loads(data)

        bg_job_id = self.env.context.get("bg_job_id")
        job = self.env["bg.job"].browse(bg_job_id) if bg_job_id else None

        chunk_num = 0
        if job and job.batch_key:
            chunk_num = self.env["bg.job"].search_count(
                [
                    ("batch_key", "=", job.batch_key),
                    ("id", "<", job.id),
                ]
            )

        # Extract field names considering import_compat mode
        import_compat = params.get("import_compat", True)
        field_names = [f.get("name") or f.get("value") or f.get("id") for f in params["fields"]]
        if import_compat:
            field_labels = field_names
        else:
            field_names = [f.get("name") or f.get("id") for f in params["fields"]]
            field_labels = [f.get("label") or f.get("string") for f in params["fields"]]

        export_data = self.export_data(field_names).get("datas", [])

        if export_format == "csv":
            content = CSVExport().from_data(params["fields"], field_labels, export_data).encode()
            ext, mime = "csv", "text/csv;charset=utf8"
        else:
            content = json.dumps({"headers": field_labels, "rows": export_data}, cls=DateTimeEncoder).encode()
            ext, mime = "json", "application/json"

        self.env["ir.attachment"].create(
            {
                "name": f"export_{export_id}_chunk_{chunk_num}.{ext}",
                "datas": base64.b64encode(content),
                "mimetype": mime,
                "res_model": False,
                "res_id": False,
                "description": export_id,
            }
        )

        # Check if this is the last job in the batch. If so, combine all chunks into final file
        # This ensures all chunks are processed before combining them
        if job and not job._get_next_jobs():
            return self.env["ir.model"]._combine_chunks(export_id, export_format)


class IrModel(models.Model):
    _name = "ir.model"
    _inherit = "ir.model"

    @api.model
    def get_export_threshold(self):
        """Get the threshold for background export without requiring admin permissions."""
        return int(self.env["ir.config_parameter"].sudo().get_param("export_bg.record_threshold", "500"))

    @api.model
    def web_export(self, data, export_format):
        """Export records in background using chunking when threshold is exceeded.
        Creates multiple background jobs if the number of records exceeds the threshold.
        Each job processes a chunk and creates an intermediate attachment.
        The last job combines all chunks into the final export file.
        """
        params = json.loads(data)
        import_compat = params.get("import_compat", True)
        Model = self.env[params["model"]].with_context(import_compat=import_compat, **params.get("context", {}))
        ids = params.get("ids")
        domain = params.get("domain", [])
        records = Model.browse(ids) if ids else Model.search(domain)

        export_id = str(uuid.uuid4())

        # base.bg serializes its own env context into the job; propagate the
        # exact model context used for export so nested relational fields are
        # resolved exactly as in synchronous exports.
        return (
            self.env["base.bg"]
            .with_context(**Model.env.context)
            .bg_enqueue_records(
                records,
                "_export_chunk_bg",
                threshold=self.get_export_threshold(),
                data=data,
                export_id=export_id,
                export_format=export_format,
            )
        )

    def _combine_chunks(self, export_id, export_format):
        """Combine all export chunks into a single file.
        For CSV: concatenates all chunks, removing headers from subsequent chunks.
        For XLSX: creates a new workbook and writes all rows from all chunks.
        """
        chunks = self.env["ir.attachment"].search([("description", "=", export_id)], order="name")

        if not chunks:
            return Markup(f'<p>{_("No data to export.")}</p>')

        if export_format == "csv":
            combined = b"".join(
                base64.b64decode(c.datas) if i == 0 else b"\n".join(base64.b64decode(c.datas).split(b"\n")[1:])
                for i, c in enumerate(chunks)
            )
            chunks.unlink()
            return self._save_attachment(combined, ".csv", "text/csv;charset=utf8")
        else:
            buf = io.BytesIO()
            wb = xlsxwriter.Workbook(buf, {"in_memory": True})
            ws = wb.add_worksheet()
            row_num = 0
            for chunk in chunks:
                chunk_data = json.loads(base64.b64decode(chunk.datas))
                if row_num == 0:
                    ws.write_row(0, 0, chunk_data["headers"])
                    row_num = 1
                for row in chunk_data["rows"]:
                    cleaned_row = [str(cell) if isinstance(cell, (dict, list)) else cell for cell in row]
                    ws.write_row(row_num, 0, cleaned_row)
                    row_num += 1
            wb.close()
            chunks.unlink()
            return self._save_attachment(
                buf.getvalue(), ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    def _save_attachment(self, content, ext, mime):
        att = self.env["ir.attachment"].create(
            {"name": f"export{ext}", "datas": base64.b64encode(content), "mimetype": mime}
        )
        return Markup(
            f'<p>{_("Your export is ready!")}</p><p><a href="/web/content/{att.id}?download=true" class="btn btn-primary"><i class="fa fa-download"/> {_("Download")} {att.name}</a></p>'
        )
