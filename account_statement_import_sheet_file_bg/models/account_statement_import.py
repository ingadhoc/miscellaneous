# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import base64
from io import BytesIO

from markupsafe import Markup
from odoo import _, models
from odoo.exceptions import UserError
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
                # Get row limit from system parameter
                rows_limit = (
                    self.env["ir.config_parameter"]
                    .sudo()
                    .get_param("account_statement_import_sheet_file_bg.rows_per_file_limit")
                )
                # Only split if parameter exists and has a valid value
                files = []
                if rows_limit:
                    try:
                        rows_limit = int(rows_limit)
                        files = self.split_base64_excel(header_column, rows_limit)
                    except (ValueError, TypeError):
                        files = []

                if files:
                    for idx, file in enumerate(files):
                        # Encode the file to string format, because background jobs cannot
                        # be executed if the parameters passed are not serializable (the original format is bytes).
                        # It is decoded back in import_file_button to be processed normally.
                        csv_or_xls = None
                        file_str = file
                        if not isinstance(file, str):
                            try:
                                file_bytes = base64.b64decode(file)
                                file_str = file_bytes.decode("utf-8")
                                csv_or_xls = "csv"
                            except Exception:
                                file_str = base64.b64encode(file_bytes).decode("ascii")
                                csv_or_xls = "xls"

                        # Create wizard data to be passed to bg job
                        wizard_data = {
                            "statement_file": file_str,
                            "statement_filename": self.statement_filename,
                            "sheet_mapping_id": self.sheet_mapping_id.id,
                            "part_number": idx + 1,
                            "total_parts": len(files),
                            "csv_or_xls": csv_or_xls,
                        }
                        # Call bg_enqueue on empty recordset and pass data as kwargs
                        # Add part number to job name for clarity
                        job_name = f"{self._name}.import_file_button - Part {idx + 1}/{len(files)}"
                        self.env[self._name].bg_enqueue(
                            "import_file_button",
                            wizard_data=wizard_data,
                            name=job_name,
                            max_retries=5,
                        )
                    # Return notification about all jobs enqueued
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": _("Process sent to background successfully"),
                            "type": "success",
                            "message": _("Processing %s files. You will be notified when each is done.") % len(files),
                            "next": {"type": "ir.actions.act_window_close"},
                        },
                    }
                # Pass wizard data for single file
                wizard_data = {
                    "statement_file": self.statement_file,
                    "statement_filename": self.statement_filename,
                    "sheet_mapping_id": self.sheet_mapping_id.id if self.sheet_mapping_id else False,
                }
                res, job = self.env[self._name].bg_enqueue("import_file_button", wizard_data=wizard_data)
                return res
            # No sheet_mapping_id, pass basic data
            wizard_data = {
                "statement_file": self.statement_file,
                "statement_filename": self.statement_filename,
            }
            res, job = self.env[self._name].bg_enqueue("import_file_button", wizard_data=wizard_data)
            return res
        else:
            # Running in background job - recreate wizard from passed data
            part_number = None
            total_parts = None
            if wizard_data:
                # Extract part info before creating wizard
                part_number = wizard_data.pop("part_number", None)
                total_parts = wizard_data.pop("total_parts", None)
                csv_or_xls = wizard_data.pop("csv_or_xls", None)
                # Decode file from string back to bytes based on file type
                statement_file = wizard_data.get("statement_file")
                if statement_file and isinstance(statement_file, str):
                    if csv_or_xls == "csv":
                        # CSV files use UTF-8 encoding
                        wizard_data["statement_file"] = base64.b64encode(statement_file.encode("utf-8"))
                    elif csv_or_xls == "xls":
                        # Excel files are already base64 encoded as ASCII strings
                        wizard_data["statement_file"] = statement_file.encode("ascii")
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
                    statement = self.env["account.bank.statement"].browse(statement_id)

                    # Add part info to statement name if split was done
                    if part_number and total_parts:
                        part_suffix = f" - Part {part_number}/{total_parts}"
                        statement.write({"name": statement.name + part_suffix})

                    base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                    url = f"{base_url}/odoo/account.bank.statement/{statement_id}"
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
        Returns empty list if file is not a valid Excel or if split is not needed.
        Only processes rows where the date column is not empty."""
        if not self.statement_file:
            return []

        output_base64_list = []
        try:
            file_bytes = base64.b64decode(self.statement_file)
            read_buffer = BytesIO(file_bytes)
            input_workbook = load_workbook(read_buffer)
            input_worksheet = input_workbook.active
        except Exception:
            return [self.statement_file]

        all_rows = list(input_worksheet.rows)
        if not all_rows:
            return []

        header_rows = all_rows[:header_rows_count]
        data_rows = all_rows[header_rows_count:]

        # Get the date column index from the sheet mapping using the parser's method
        parser = self.env["account.statement.import.sheet.parser"]
        header = parser.parse_header((input_workbook, input_worksheet), self.sheet_mapping_id)
        try:
            date_column_indexes = parser._get_column_indexes(header, "timestamp_column", self.sheet_mapping_id)
            date_column_index = date_column_indexes[0] if date_column_indexes else None
        except Exception as e:
            raise UserError(_("Error importing bank statement: %s") % str(e))

        # Filter out rows where the date column is empty
        data_rows = self._filter_rows_with_date(data_rows, date_column_index)

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

    def _filter_rows_with_date(self, data_rows, date_column_index):
        """Filter data rows to only include rows where the date column is not empty.
        If date_column_index is None, return all rows."""
        if date_column_index is None:
            return data_rows

        filtered_rows = []
        for row in data_rows:
            # Check if the row has enough columns and the date column is not empty
            if len(row) > date_column_index and row[date_column_index].value:
                filtered_rows.append(row)
            elif len(row) > date_column_index and not row[date_column_index].value:
                # Stop processing when we find the first empty date
                break

        return filtered_rows
