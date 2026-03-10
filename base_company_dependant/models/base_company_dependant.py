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
import json
import logging

from odoo import api, models
from odoo.fields import Domain
from psycopg2 import sql

_logger = logging.getLogger(__name__)


class BaseCompanyDependant(models.AbstractModel):
    """Proporciona métodos de backend para leer y escribir campos
    company_dependent accediendo directamente a la columna JSONB,
    sin pasar por la resolución del ORM (que devuelve el valor ya
    resuelto para la compañía activa).

    Se expone como AbstractModel para poder extenderse en otros módulos,
    pero los métodos @api.model se pueden invocar directamente via RPC
    desde el frontend usando ``env['base.company.dependant'].call(...)``.
    """

    _name = "base.company.dependant"
    _description = "Helpers para campos company_dependent"

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _get_raw_json(self, model_table, field_name, res_id):
        """Lee la columna JSONB cruda para un registro sin pasar por el ORM."""
        self.env.cr.execute(
            sql.SQL("SELECT {col} FROM {table} WHERE id = %s").format(
                col=sql.Identifier(field_name),
                table=sql.Identifier(model_table),
            ),
            (res_id,),
        )
        row = self.env.cr.fetchone()
        if not row or row[0] is None:
            return {}
        return dict(row[0])

    def _write_raw_json(self, model_table, field_name, res_id, raw_json):
        """Escribe la columna JSONB cruda directamente, luego invalida la caché."""
        self.env.cr.execute(
            sql.SQL("UPDATE {table} SET {col} = %s WHERE id = %s").format(
                col=sql.Identifier(field_name),
                table=sql.Identifier(model_table),
            ),
            (json.dumps(raw_json), res_id),
        )

    def _resolve_m2o_display(self, comodel_name, value_id):
        """Devuelve el display_name de un registro Many2one, o None si no existe."""
        if not value_id:
            return None
        try:
            record = self.env[comodel_name].sudo().browse(int(value_id))
            if record.exists():
                return record.display_name
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # API pública (llamada desde el frontend via RPC)
    # ------------------------------------------------------------------

    @api.model
    def get_company_dependent_values(self, res_model, res_id, field_name):
        """Retorna los valores por compañía para un campo company_dependent.

        Solo se incluyen las compañías a las que el usuario tiene acceso
        (``self.env.companies``).

        :param res_model: Nombre técnico del modelo (ej. 'product.category').
        :param res_id: ID del registro.
        :param field_name: Nombre técnico del campo.
        :returns: dict con claves:
            - ``values``: lista de dicts por compañía (ver abajo).
            - ``field_type``: 'many2one', 'float', 'integer', etc.
            - ``comodel_name``: modelo del Many2one (solo si aplica).
        """
        self.env["ir.model.access"].check(res_model, "read")
        model_obj = self.env[res_model]
        field = model_obj._fields.get(field_name)

        if not field or not field.company_dependent:
            raise ValueError(f"El campo '{field_name}' en '{res_model}' no es company_dependent.")

        raw_json = self._get_raw_json(model_obj._table, field_name, res_id)

        # Fallback global: ir.default
        fallback_value = self.env["ir.default"]._get(res_model, field_name)

        values = []
        for company in self.env.companies:
            company_key = str(company.id)
            is_specific = company_key in raw_json
            raw_val = raw_json[company_key] if is_specific else fallback_value

            value_id = None
            display_value = None

            if field.type == "many2one":
                if is_specific:
                    # Valor almacenado explícitamente para esta compañía.
                    # raw_val == False significa «vacío explícito»; value_id permanece None.
                    if raw_val:
                        value_id = int(raw_val)
                        display_value = self._resolve_m2o_display(field.comodel_name, value_id)
                else:
                    # Valor heredado del fallback global (ir.default).
                    # ir.default._get puede devolver un entero, un recordset o None/False.
                    if fallback_value:
                        try:
                            fb_id = fallback_value.id if hasattr(fallback_value, "id") else int(fallback_value)
                            value_id = fb_id
                            display_value = self._resolve_m2o_display(field.comodel_name, fb_id)
                        except (TypeError, ValueError):
                            pass
            elif field.type in ("float", "integer"):
                raw_val = raw_json[company_key] if is_specific else fallback_value
                value_id = raw_val
                display_value = str(raw_val) if raw_val is not None else None

            # Domain efectivo para el autocomplete de esta fila:
            # domain estático del campo + domain de compañía concreta.
            # Ambos lados se normalizan con Domain() para soportar el caso en que
            # _check_company_domain esté sobreescrito y devuelva una list.
            row_domain = []
            if field.type == "many2one":
                comodel = self.env[field.comodel_name]
                static_domain = Domain(field.get_comodel_domain(model_obj))
                company_domain = Domain(comodel._check_company_domain(company))
                row_domain = list(static_domain & company_domain)

            values.append(
                {
                    "company_id": company.id,
                    "company_name": company.name,
                    "is_specific": is_specific,
                    "value_id": value_id,
                    "display_value": display_value,
                    "domain": row_domain,
                }
            )

        comodel_name = field.comodel_name if field.type == "many2one" else None

        return {
            "values": values,
            "field_type": field.type,
            "comodel_name": comodel_name,
        }

    @api.model
    def _get_field_domain_for_company(self, res_model, field_name, company_id):
        """Devuelve el domain efectivo para un campo Many2one company_dependent,
        combinando el domain estático del campo con el domain de compañía.

        Equivale a: field_domain + comodel._check_company_domain(company)

        :param res_model: nombre técnico del modelo (ej. 'product.category').
        :param field_name: nombre técnico del campo.
        :param company_id: ID de la compañía para la que se calcula el domain.
        :returns: domain serializado como lista de tuplas.
        """
        model_obj = self.env[res_model]
        field = model_obj._fields.get(field_name)
        if not field or field.type != "many2one":
            return []

        company = self.env["res.company"].browse(company_id)
        comodel = self.env[field.comodel_name]

        # Normalizamos con Domain() para soportar overrides que devuelvan lista
        static_domain = Domain(field.get_comodel_domain(model_obj))
        company_domain = Domain(comodel._check_company_domain(company))

        effective = static_domain & company_domain
        return list(effective)

    @api.model
    def set_company_dependent_values(self, res_model, res_id, field_name, values_dict):
        """Guarda valores por compañía para un campo company_dependent.

        :param values_dict: dict ``{str(company_id): value}`` donde *value* puede ser:
            - Un ID de registro (Many2one).
            - ``False``: guarda la clave como ``false`` en el JSON (vacío explícito).
            - ``"RESET"``: **elimina** la clave del JSON (restaura al fallback).
        """
        self.env["ir.model.access"].check(res_model, "write")
        model_obj = self.env[res_model]
        field = model_obj._fields.get(field_name)

        if not field or not field.company_dependent:
            raise ValueError(f"El campo '{field_name}' en '{res_model}' no es company_dependent.")

        raw_json = self._get_raw_json(model_obj._table, field_name, res_id)

        for company_id_str, value in values_dict.items():
            key = str(company_id_str)
            if value == "RESET":
                raw_json.pop(key, None)
            else:
                raw_json[key] = value

        self._write_raw_json(model_obj._table, field_name, res_id, raw_json)

        # Invalida la caché del ORM para que la vista se refresque con el nuevo valor.
        model_obj.browse(res_id).invalidate_recordset([field_name])
        return True

    @api.model
    def get_company_dependent_meta(self, res_model, res_id):
        """Retorna un dict ``{field_name: is_specific}`` para todos los campos
        company_dependent del modelo, indicando si la compañía actual tiene un
        valor explícito en el JSON.

        Usa una sola query SQL para no generar N+1 consultas.
        """
        self.env["ir.model.access"].check(res_model, "read")
        model_obj = self.env[res_model]
        company_key = str(self.env.company.id)

        cd_fields = [name for name, f in model_obj._fields.items() if f.company_dependent and f.store]
        if not cd_fields:
            return {}

        # Una sola SELECT para todos los campos company_dependent
        self.env.cr.execute(
            sql.SQL("SELECT {cols} FROM {table} WHERE id = %s").format(
                cols=sql.SQL(", ").join(sql.Identifier(f) for f in cd_fields),
                table=sql.Identifier(model_obj._table),
            ),
            (res_id,),
        )
        row = self.env.cr.fetchone()
        if not row:
            return {}

        return {field_name: (company_key in (row[i] or {})) for i, field_name in enumerate(cd_fields)}
