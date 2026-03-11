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
import ast
import json
import logging

from odoo import api, models
from odoo.fields import Domain
from psycopg2 import sql

_logger = logging.getLogger(__name__)


class BaseCompanyDependent(models.AbstractModel):
    """Proporciona métodos de backend para leer y escribir campos
    company_dependent accediendo directamente a la columna JSONB,
    sin pasar por la resolución del ORM (que devuelve el valor ya
    resuelto para la compañía activa).

    Se expone como AbstractModel para poder extenderse en otros módulos,
    pero los métodos @api.model se pueden invocar directamente via RPC
    desde el frontend usando ``env['base.company.dependent'].call(...)``.
    """

    _name = "base.company.dependent"
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

    def _get_field_static_domain(self, field, model_obj):
        """Devuelve el domain estático de un campo relacional como objeto Domain.

        Maneja los tres formatos posibles del atributo ``field.domain``:

        * **Callable** → se llama con ``model_obj`` y el resultado se convierte.
        * **list / Domain** → se usa directamente.
        * **str** → se parsea con ``ast.literal_eval``.
          En Odoo 19, ``get_comodel_domain`` descarta los dominios string con
          un ``return Domain.TRUE`` (los considera solo para el cliente), por lo
          que es imprescindible este paso adicional.
        """
        raw = field.domain

        # --- callable (puede devolver list, Domain o incluso str) ---
        if callable(raw):
            try:
                raw = raw(model_obj)
            except Exception:
                return Domain.TRUE

        # --- Domain / list ---
        if isinstance(raw, (Domain, list)) and raw:
            try:
                return Domain(raw)
            except Exception:
                return Domain.TRUE

        # --- string: parsear con ast.literal_eval (dominios simples) ---
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = ast.literal_eval(raw.strip())
                return Domain(parsed)
            except (ValueError, SyntaxError):
                pass

        return Domain.TRUE

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

        values = []
        for company in self.env.companies:
            company_key = str(company.id)
            is_specific = company_key in raw_json

            # El fallback se resuelve usando el mismo mecanismo que el ORM en SQL:
            # COALESCE(jsonb->company_id, to_jsonb(ir_default_fallback)).
            # get_company_dependent_fallback lee ir.default con SUPERUSER, igual
            # que hace el ORM al evaluar el campo, garantizando consistencia.
            model_with_company = model_obj.with_company(company)
            try:
                fallback_rec = field.get_company_dependent_fallback(model_with_company)
                fallback_value = field.convert_to_write(fallback_rec, model_with_company)
            except Exception:
                fallback_value = None

            raw_val = raw_json[company_key] if is_specific else fallback_value

            value_id = None
            display_value = None
            fallback_value_id = None
            fallback_display_value = None

            if field.type == "many2one":
                # Siempre calculamos el fallback para poder mostrarlo al resetear.
                if fallback_value:
                    try:
                        fb_id = fallback_value.id if hasattr(fallback_value, "id") else int(fallback_value)
                        fallback_value_id = fb_id
                        fallback_display_value = self._resolve_m2o_display(field.comodel_name, fb_id)
                    except (TypeError, ValueError):
                        pass

                if is_specific:
                    # Valor almacenado explícitamente para esta compañía.
                    # raw_val == False significa «vacío explícito»; value_id permanece None.
                    if raw_val:
                        value_id = int(raw_val)
                        display_value = self._resolve_m2o_display(field.comodel_name, value_id)
                else:
                    # Valor heredado del fallback global (ir.default).
                    value_id = fallback_value_id
                    display_value = fallback_display_value
            elif field.type in ("float", "integer"):
                raw_val = raw_json[company_key] if is_specific else fallback_value
                value_id = raw_val
                display_value = str(raw_val) if raw_val is not None else None
                fallback_value_id = fallback_value
                fallback_display_value = str(fallback_value) if fallback_value is not None else None

            # Domain efectivo para el autocomplete de esta fila:
            # domain estático del campo + domain de compañía concreta.
            # _get_field_static_domain maneja dominios string, list y callable.
            row_domain = []
            if field.type == "many2one":
                comodel = self.env[field.comodel_name]
                static_domain = self._get_field_static_domain(field, model_obj)
                company_domain = Domain(comodel._check_company_domain(company))
                row_domain = list(static_domain & company_domain)

            values.append(
                {
                    "company_id": company.id,
                    "company_name": company.name,
                    "is_specific": is_specific,
                    "value_id": value_id,
                    "display_value": display_value,
                    "fallback_value_id": fallback_value_id,
                    "fallback_display_value": fallback_display_value,
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

        # _get_field_static_domain maneja dominios string, list y callable
        static_domain = self._get_field_static_domain(field, model_obj)
        company_domain = Domain(comodel._check_company_domain(company))

        effective = static_domain & company_domain
        return list(effective)

    @api.model
    def set_company_dependent_values(self, res_model, res_id, field_name, values_dict):
        """Guarda valores por compañía para un campo company_dependent.

        Para valores explícitos (IDs o False) se usa el ORM con ``with_company``
        de modo que los checks de compañía y las reglas de acceso se ejecuten
        correctamente. Solo el caso ``"RESET"`` (eliminar la clave del JSON)
        requiere una escritura directa, ya que el ORM no expone esa operación.

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

        record = model_obj.browse(res_id)

        # Sanitize corrupted JSONB: replace boolean `false` with `null` so the
        # ORM can read the field without a PostgreSQL cast error (Many2one
        # columns expect integer or null, not boolean).
        if field.type == "many2one":
            raw_json = self._get_raw_json(model_obj._table, field_name, res_id)
            sanitized = {k: (None if v is False else v) for k, v in raw_json.items()}
            if sanitized != raw_json:
                self._write_raw_json(model_obj._table, field_name, res_id, sanitized)
                record.invalidate_recordset([field_name])

        for company_id_str, value in values_dict.items():
            company_id = int(company_id_str)
            company = self.env["res.company"].browse(company_id)
            record_with_company = record.with_company(company)

            if value == "RESET":
                # RESET: eliminar la clave de la compañía del JSONB para que
                # el campo vuelva al fallback global (ir.default / COALESCE).
                #
                # Intentamos primero la vía ORM: escribir el valor de fallback
                # hace que el UPDATE del ORM descarte la clave cuando
                # value == fallback. Pero si el fallback es False y el valor
                # almacenado también es False (o null), el ORM no ejecuta
                # UPDATE porque no detecta cambios. En ese caso eliminamos
                # la clave directamente del JSONB.
                fallback_rec = field.get_company_dependent_fallback(record_with_company)
                write_val = field.convert_to_write(fallback_rec, record_with_company)
                record_with_company.write({field_name: write_val})

                # Verificar si la clave sigue en el JSONB (el ORM no la eliminó).
                raw_json = self._get_raw_json(model_obj._table, field_name, res_id)
                if str(company_id) in raw_json:
                    del raw_json[str(company_id)]
                    self._write_raw_json(model_obj._table, field_name, res_id, raw_json)
                    record.invalidate_recordset([field_name])
            else:
                # Valor explícito (ID o False): usamos el ORM con with_company
                # para que check_company, ondelete y demás validaciones se apliquen.
                record_with_company.write({field_name: value})
                # El ORM descarta la clave del JSONB cuando value == fallback.
                # En ese caso forzamos la clave via raw SQL para que la asignación
                # explícita sobreviva a futuros cambios del valor por defecto.
                fallback_rec = field.get_company_dependent_fallback(record_with_company)
                fallback_column = field.convert_to_column(
                    field.convert_to_write(fallback_rec, record_with_company),
                    record_with_company,
                )
                write_column = field.convert_to_column(value, record_with_company)
                if write_column == fallback_column:
                    raw_json = self._get_raw_json(model_obj._table, field_name, res_id)
                    raw_json[str(company_id)] = write_column  # None → null en JSON
                    self._write_raw_json(model_obj._table, field_name, res_id, raw_json)
                    record.invalidate_recordset([field_name])

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
