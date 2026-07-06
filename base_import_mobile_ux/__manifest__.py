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
    "name": "Base Import Mobile UX",
    "version": "19.0.1.0.0",
    "category": "Base",
    "author": "ADHOC SA",
    "website": "https://www.adhoc.com.ar",
    "license": "AGPL-3",
    "summary": "Show the Import action in the list view gear menu on small screens",
    "depends": [
        "base_import",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "base_import_mobile_ux/static/src/import_records.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
