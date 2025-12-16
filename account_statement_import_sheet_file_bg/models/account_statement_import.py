# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import base64
from io import BytesIO

from markupsafe import Markup
from odoo import _, models
from openpyxl import Workbook, load_workbook


class AccountStatementImport(models.TransientModel):
    _name = "account.statement.import"
    _inherit = ["account.statement.import", "base.bg"]

    def import_file_button(self, wizard_data=None):
        """Process the file chosen in the wizard, create a bank statement
        and return a link to its reconciliation page."""
        if not self._context.get("bg_job"):
            if self.sheet_mapping_id:
                header_column = self.sheet_mapping_id.header_lines_skip_count
                files = self.split_base64_excel(header_column, 1000)
                if files:
                    res = False
                    for file in files:
                        # Create wizard data to be passed to bg job
                        wizard_data = {
                            "statement_file": file,
                            "statement_filename": self.statement_filename,
                            "sheet_mapping_id": self.sheet_mapping_id.id,
                        }
                        # Call bg_enqueue on empty recordset and pass data as kwargs
                        res = self.env[self._name].bg_enqueue("import_file_button", wizard_data=wizard_data)
                    return res
                # Pass wizard data for single file
                wizard_data = {
                    "statement_file": self.statement_file,
                    "statement_filename": self.statement_filename,
                    "sheet_mapping_id": self.sheet_mapping_id.id if self.sheet_mapping_id else False,
                }
                return self.env[self._name].bg_enqueue("import_file_button", wizard_data=wizard_data)
            # No sheet_mapping_id, pass basic data
            wizard_data = {
                "statement_file": self.statement_file,
                "statement_filename": self.statement_filename,
            }
            return self.env[self._name].bg_enqueue("import_file_button", wizard_data=wizard_data)
        else:
            # Running in background job - recreate wizard from passed data
            if wizard_data:
                wizard = self.create(wizard_data)
            else:
                wizard = self
            try:
                result = super(AccountStatementImport, wizard).import_file_button()

                statement_id = False

                if result and result.get("domain"):
                    for dom in result["domain"]:
                        if dom[0] == "id" and dom[1] == "in" and dom[2]:
                            statement_id = dom[2][0]
                            break

                if statement_id:
                    base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                    url = f"{base_url}/odoo/account.bank.statement/{statement_id}"

                    statement = self.env["account.bank.statement"].browse(statement_id)
                    name = statement.name or f"Statement {statement_id}"

                    res_html = (
                        "The following bank statement has been created:<br>"
                        f'<a href="{url}" target="_blank">{name}</a><br>'
                    )

                    return Markup(res_html)
            except Exception as e:
                return _("Error importing bank statement: %s") % str(e)
            return result

    def split_base64_excel(self, header_rows_count, rows_per_file_limit):
        """Split Excel file into multiple parts to avoid overloading the system.
        Returns empty list if file is not a valid Excel or if split is not needed."""
        if not self.statement_file:
            return []

        output_base64_list = []
        try:
            file_bytes = base64.b64decode(self.statement_file)
            read_buffer = BytesIO(file_bytes)
            input_workbook = load_workbook(read_buffer)
            input_worksheet = input_workbook.active
        except Exception:
            return []

        all_rows = list(input_worksheet.rows)
        if not all_rows:
            return []

        header_rows = all_rows[:header_rows_count]
        data_rows = all_rows[header_rows_count:]
        start_row_index = 0
        total_data_rows = len(data_rows)

        while start_row_index < total_data_rows:
            end_row_index = min(start_row_index + rows_per_file_limit, total_data_rows)
            rows_for_current_part = data_rows[start_row_index:end_row_index]

            output_workbook = Workbook()
            output_worksheet = output_workbook.active

            for header_row in header_rows:
                row_values = [cell.value for cell in header_row]
                output_worksheet.append(row_values)

            for data_row in rows_for_current_part:
                row_values = [cell.value for cell in data_row]
                output_worksheet.append(row_values)

            write_buffer = BytesIO()
            output_workbook.save(write_buffer)
            output_bytes = write_buffer.getvalue()
            base64_content = base64.b64encode(output_bytes).decode("utf-8")
            output_base64_list.append(base64_content)

            start_row_index = end_row_index
        return output_base64_list
