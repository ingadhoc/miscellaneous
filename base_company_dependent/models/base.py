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
from odoo import _, api, models
from odoo.exceptions import ValidationError


class Base(models.AbstractModel):
    """Exposes ``company_dependent`` to the frontend widget and blocks
    cross-company contamination on imports (UI and module CSV data) by
    validating company_dependent Many2one values inside ``load()``."""

    _inherit = "base"

    @api.model
    def _get_view_field_attributes(self):
        keys = super()._get_view_field_attributes()
        keys.append("company_dependent")
        return keys

    @api.model
    def load(self, fields, data):
        result = super().load(fields, data)
        loaded_ids = [rid for rid in (result.get("ids") or []) if rid]
        if loaded_ids:
            self.browse(loaded_ids)._check_company_dependent_m2o()
        return result

    def _check_company_dependent_m2o(self):
        """Raise ValidationError if any company_dependent Many2one on this
        recordset belongs to a company other than ``self.env.company``."""
        company = self.env.company
        cd_fields = [f for f in self._fields.values() if f.type == "many2one" and f.company_dependent]
        for field in cd_fields:
            comodel = self.env[field.comodel_name]
            if "company_id" not in comodel and "company_ids" not in comodel:
                # comodel shared by every company: nothing to cross-check
                continue
            company_domain = comodel._check_company_domain(company)
            if not company_domain:
                continue
            for record in self:
                # sudo to bypass ir.rules on the m2o target; company context is preserved
                value = record.sudo()[field.name]
                if not value:
                    continue
                if (
                    comodel.sudo()
                    .with_context(active_test=False)
                    .search(company_domain + [("id", "=", value.id)], limit=1)
                ):
                    continue
                raise ValidationError(
                    _(
                        "%(field)s '%(value)s' belongs to a different company "
                        "and cannot be used with company '%(company)s'.",
                        field=field.string,
                        value=value.display_name,
                        company=company.name,
                    )
                )
