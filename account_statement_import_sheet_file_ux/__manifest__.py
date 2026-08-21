##############################################################################
#
#    Copyright (C) 2026  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "Bank Statement Sheet Import UX",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "Preview and test import of a statement sheet mapping, plus "
    "usability fixes on the mapping configuration, the column parser and the "
    "statement import itself",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "external_dependencies": {"python": ["xlsxwriter"]},
    "depends": [
        "account_statement_import_file",
        "account_statement_import_sheet_file",
        "account_statement_import_sheet_file_xls",
        "account_statement_import_sheet_file_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_statement_import_sheet_mapping_preview_views.xml",
        "views/account_statement_import_sheet_mapping_views.xml",
        "views/account_statement_import_views.xml",
    ],
    "installable": True,
    "auto_install": ["account_statement_import_sheet_file"],
    "application": False,
}
