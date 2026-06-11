##############################################################################
#
#    Copyright (C) 2024  ADHOC SA  (http://www.adhoc.com.ar)
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
    "name": "Base Company Dependent UX",
    "version": "19.0.1.2.0",
    "category": "Base",
    "sequence": 14,
    "summary": (
        "Mejora UX de campos company_dependent: indicador visual y asistente "
        "multicompañía para gestionar valores por compañía sin cambiar de sesión."
    ),
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": ["base", "web", "product"],
    "assets": {
        "web.assets_backend": [
            "base_company_dependent/static/src/**/*",
        ],
    },
    "data": [
        "views/product_template_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
