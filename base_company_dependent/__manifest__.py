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
<<<<<<< 208b26e0e55785923fe13f62205ef33006ebee79
    "version": "20.0.1.0.0",
||||||| 01ef66dbf3ec84f203e9b3c63c47739c308d4150
    "version": "19.0.1.1.0",
=======
    "version": "19.0.1.2.0",
>>>>>>> 2f7d49b093ce9012e8d29e591ffb369db801f4d9
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
    "depends": ["base", "web"],
    "assets": {
        "web.assets_backend": [
            "base_company_dependent/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "base_company_dependent/static/tests/**/*",
        ],
    },
    "data": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
