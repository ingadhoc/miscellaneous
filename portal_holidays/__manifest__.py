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
    'name': 'Portal Holidays',
<<<<<<< HEAD
    'version': '13.0.1.0.0',
||||||| parent of 0883742... temp
    'version': '13.0.1.1.0',
=======
    'version': '13.0.1.2.0',
>>>>>>> 0883742... temp
    'category': 'Base',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'portal_backend',
        'hr_holidays',
    ],
    'data': [
        'security/portal_holidays.xml',
        'security/ir.model.access.csv',
        'views/portal_templates.xml',
    ],
    'installable': False,
    'auto_install': False,
    'application': False,
}
