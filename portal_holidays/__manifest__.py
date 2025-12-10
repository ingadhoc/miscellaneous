##############################################################################
#
#    Copyright (C) 2019  ADHOC SA  (http://www.adhoc.com.ar)
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
    "name": "Portal Holidays",
<<<<<<< 48e87b28d371901ad6ea6f896bb13dcc8bb3580d
    "version": "19.0.1.0.0",
||||||| 32d3a6492d218095eca4c7bcf23257ed29a2f3bd
    "version": "18.0.1.5.0",
=======
    "version": "18.0.1.6.0",
>>>>>>> 15305f046af102d97d6b2f5f553bb93cd75e30a7
    "category": "Base",
    "sequence": 14,
    "summary": "",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": ["portal_backend", "hr_holidays", "hr_holidays_attendance"],
    "data": [
        "security/res_groups.xml",
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        "views/hr_employee_views.xml",
        "views/portal_holidays_views.xml",
        "views/base_menus.xml",
    ],
    "demo": [
        "demo/hr_demo.xml",
        "demo/res_users_demo.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
