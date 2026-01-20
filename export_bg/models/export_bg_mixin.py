import base64
import io
import json

import xlsxwriter
from markupsafe import Markup
from odoo import _, api, models
from odoo.addons.web.controllers.export import CSVExport


class IrModel(models.Model):
    _name = "ir.model"
    _inherit = ["ir.model", "base.bg"]

    @api.model
    def get_export_threshold(self):
        """Get the threshold for background export without requiring admin permissions."""
        return int(self.env["ir.config_parameter"].sudo().get_param("export_bg.record_threshold", "500"))

    def _prepare_export_data(self, data):
        params = json.loads(data)
        Model = self.env[params["model"]].with_context(**params.get("context", {}))
        records = Model.browse(params["ids"]) if params.get("ids") else Model.search(params.get("domain", []))

        # Support both 'name' and 'value' keys for field names (templates use 'name', regular exports use 'value')
        field_names = [f.get("name") or f.get("value") or f.get("id") for f in params["fields"]]
        field_labels = [f.get("label") or f.get("string") for f in params["fields"]]

        return (
            params,
            field_labels,
            records.export_data(field_names).get("datas", []),
        )

    def web_export_csv(self, data):
        params, headers, export_data = self._prepare_export_data(data)
        content = CSVExport().from_data(params["fields"], headers, export_data).encode()
        return self._save_attachment(params["model"], content, ".csv", "text/csv;charset=utf8")

    def web_export_xlsx(self, data):
        params, headers, export_data = self._prepare_export_data(data)
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        ws = wb.add_worksheet()
        ws.write_row(0, 0, headers)
        for i, row in enumerate(export_data, 1):
            ws.write_row(i, 0, row)
        wb.close()
        return self._save_attachment(
            params["model"],
            buf.getvalue(),
            ".xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _save_attachment(self, model, content, ext, mime):
        att = self.env["ir.attachment"].create(
            {"name": f"{model}{ext}", "datas": base64.b64encode(content), "mimetype": mime}
        )
        return Markup(
            f'<p>{_("Your export is ready!")}</p><p><a href="/web/content/{att.id}?download=true" class="btn btn-primary"><i class="fa fa-download"/> {_("Download")} {att.name}</a></p>'
        )
