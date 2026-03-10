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
from odoo import api, models


class Base(models.AbstractModel):
    """Expone el atributo ``company_dependent`` al cliente web.

    ``_get_view_field_attributes`` controla qué metadatos de campo se incluyen
    en la respuesta del ORM al cargar una vista.  ``company_dependent`` no está
    en la lista base de Odoo 19, por lo que el frontend nunca lo recibe y no
    puede activar el widget multicompañía.
    """

    _inherit = "base"

    @api.model
    def _get_view_field_attributes(self):
        keys = super()._get_view_field_attributes()
        keys.append("company_dependent")
        return keys
