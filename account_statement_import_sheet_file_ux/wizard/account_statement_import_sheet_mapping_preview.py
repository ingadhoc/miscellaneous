import base64
import io
from urllib.parse import urlencode

import xlsxwriter
from odoo import api, fields, models


class AccountStatementImportSheetMappingPreview(models.TransientModel):
    _name = "account.statement.import.sheet.mapping.preview"
    _description = "Bank Statement Import Sheet Mapping Preview"

    mapping_id = fields.Many2one(
        comodel_name="account.statement.import.sheet.mapping",
        string="Mapping",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    preview_html = fields.Html(
        string="Preview",
        compute="_compute_preview_html",
        sanitize=False,
    )
    file_data = fields.Binary(string="Sample File", readonly=True, attachment=False)

    @api.depends("mapping_id")
    def _compute_preview_html(self):
        for preview in self:
            preview.preview_html = self.env["ir.qweb"]._render(
                "account_statement_import_sheet_file_ux.mapping_preview",
                preview.mapping_id._preview_layout(),
            )

    def _build_xlsx(self):
        """Return the sample sheet as xlsx bytes.

        Every cell is written as text on purpose: that is how the parser reads
        the file, so the sample can be imported with this very mapping.
        """
        self.ensure_one()
        layout = self.mapping_id._preview_grid()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet(self.env._("Statement"))
        header_format = workbook.add_format({"bold": True, "border": 1})
        for index in range(len(layout["letters"])):
            sheet.set_column(index, index, 18)
        for row in layout["rows"]:
            for index, value in enumerate(row["cells"]):
                if not value:
                    continue
                sheet.write_string(
                    row["number"] - 1,
                    index,
                    value,
                    header_format if row["kind"] == "header" else None,
                )
        workbook.close()
        return output.getvalue()

    def action_download_xlsx(self):
        self.ensure_one()
        self.file_data = base64.b64encode(self._build_xlsx())
        params = urlencode(
            {
                "model": self._name,
                "id": self.id,
                "field": "file_data",
                "filename": f"{self.mapping_id.name}.xlsx",
                "download": "true",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?{params}",
            "target": "self",
        }
