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
from odoo.exceptions import UserError, ValidationError
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
        raw = getattr(field, "domain", None)
        if raw is None:
            return Domain.TRUE

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

    # ------------------------------------------------------------------
    # Helpers de jerarquía
    # ------------------------------------------------------------------

    def _get_accessible_companies_hierarchy(self):
        """Retorna las compañías accesibles organizadas como árbol de hasta 3 niveles.

        Devuelve una lista plana ordenada por jerarquía (padre → hija → nieta),
        cada elemento con su ``parent_id`` para que el frontend pueda construir
        el árbol. Solo incluye compañías en ``self.env.companies``.
        """
        accessible = self.env.companies
        accessible_ids = set(accessible.ids)

        result = []
        for company in accessible:
            # Determinamos el nivel: 1 = sin padre accesible, 2 = padre accesible, 3 = abuelo accesible
            parent = company.parent_id
            grandparent = parent.parent_id if parent else self.env["res.company"]

            if parent and parent.id in accessible_ids:
                level = 3 if (grandparent and grandparent.id in accessible_ids) else 2
            else:
                level = 1

            # child_ids accesibles (primeros 3 niveles únicamente)
            accessible_children = [c.id for c in company.child_ids if c.id in accessible_ids]

            result.append(
                {
                    "id": company.id,
                    "parent_id": parent.id if parent and parent.id in accessible_ids else None,
                    "level": level,
                    "has_children": bool(accessible_children),
                    "child_ids": accessible_children,
                    "name": company.name,
                }
            )

        # Ordenar: primero los de nivel 1, luego 2, luego 3 (dentro de cada padre, por id)
        result.sort(key=lambda r: (r["level"], r["parent_id"] or 0, r["id"]))
        return result

    def _build_row_data(self, field, model_obj, company, raw_json):  # noqa: C901
        """Construye el dict de datos de una fila (compañía) para el diálogo."""
        company_key = str(company.id)
        is_specific = company_key in raw_json

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
        selection_options = None

        if field.type == "many2one":
            if fallback_value:
                try:
                    fb_id = fallback_value.id if hasattr(fallback_value, "id") else int(fallback_value)
                    fallback_value_id = fb_id
                    fallback_display_value = self._resolve_m2o_display(field.comodel_name, fb_id)
                except (TypeError, ValueError):
                    pass
            if is_specific:
                if raw_val:
                    value_id = int(raw_val)
                    display_value = self._resolve_m2o_display(field.comodel_name, value_id)
            else:
                value_id = fallback_value_id
                display_value = fallback_display_value

        elif field.type == "selection":
            # Calculamos las opciones y el label del valor actual
            selection_options = (
                list(field.selection)
                if isinstance(field.selection, list)
                else [(k, str(v)) for k, v in field._description_selection(model_with_company.env)]
            )
            raw_val = raw_json.get(company_key, fallback_value)
            value_id = raw_val
            # Buscar el label
            for key, label in selection_options:
                if key == raw_val:
                    display_value = str(label)
                    break
            if display_value is None and raw_val is not None:
                display_value = str(raw_val)
            # Fallback label
            if fallback_value is not None:
                fallback_value_id = fallback_value
                for key, label in selection_options:
                    if key == fallback_value:
                        fallback_display_value = str(label)
                        break

        elif field.type in ("float", "integer", "monetary"):
            raw_val = raw_json[company_key] if is_specific else fallback_value
            # Treat explicit False (JSON false) as empty — str(False) = "False" in inputs
            if raw_val is False:
                raw_val = None
            value_id = raw_val
            display_value = str(raw_val) if raw_val is not None else ""
            fv = fallback_value if fallback_value is not False else None
            fallback_value_id = fv
            fallback_display_value = str(fv) if fv is not None else ""

        elif field.type == "boolean":
            raw_val = raw_json[company_key] if is_specific else fallback_value
            value_id = bool(raw_val) if raw_val is not None else False
            display_value = str(value_id)
            fallback_value_id = bool(fallback_value) if fallback_value is not None else False
            fallback_display_value = str(fallback_value_id)

        elif field.type in ("char", "text"):
            raw_val = raw_json[company_key] if is_specific else fallback_value
            value_id = raw_val
            display_value = raw_val or ""
            fallback_value_id = fallback_value
            fallback_display_value = fallback_value or ""

        elif field.type == "date":
            raw_val = raw_json[company_key] if is_specific else fallback_value
            # Dates are stored as strings in JSONB; convert to string for the frontend
            if hasattr(raw_val, "isoformat"):
                raw_val = raw_val.isoformat()
            value_id = raw_val
            display_value = raw_val
            fv = fallback_value
            if hasattr(fv, "isoformat"):
                fv = fv.isoformat()
            fallback_value_id = fv
            fallback_display_value = fv

        row_domain = []
        if field.type == "many2one":
            comodel = self.env[field.comodel_name]
            static_domain = self._get_field_static_domain(field, model_obj)
            company_domain = Domain(comodel._check_company_domain(company))
            row_domain = list(static_domain & company_domain)

        row = {
            "company_id": company.id,
            "company_name": company.name,
            "is_specific": is_specific,
            "value_id": value_id,
            "display_value": display_value,
            "fallback_value_id": fallback_value_id,
            "fallback_display_value": fallback_display_value,
            "domain": row_domain,
        }
        if selection_options is not None:
            row["selection_options"] = selection_options
        return row

    @api.model
    def get_company_dependent_values(self, res_model, res_id, field_name):
        """Retorna los valores por compañía para un campo company_dependent.

        Solo se incluyen las compañías a las que el usuario tiene acceso
        (``self.env.companies``). Incluye metadatos de jerarquía para el diálogo.

        :param res_model: Nombre técnico del modelo (ej. 'product.category').
        :param res_id: ID del registro.
        :param field_name: Nombre técnico del campo.
        :returns: dict con claves:
            - ``values``: lista de dicts por compañía con datos de jerarquía.
            - ``field_type``: 'many2one', 'selection', 'float', 'integer', etc.
            - ``comodel_name``: modelo del Many2one (solo si aplica).
            - ``selection_options``: lista [(key, label)] (solo si selection).
        """
        self.env["ir.model.access"].check(res_model, "read")
        model_obj = self.env[res_model]
        model_obj.browse(res_id).check_access("read")
        field = model_obj._fields.get(field_name)

        if not field or not field.company_dependent:
            raise ValueError(f"El campo '{field_name}' en '{res_model}' no es company_dependent.")

        raw_json = self._get_raw_json(model_obj._table, field_name, res_id)

        # Mapa compañía_id → metadatos de jerarquía
        hierarchy = {h["id"]: h for h in self._get_accessible_companies_hierarchy()}

        values = []
        for company in self.env.companies:
            row = self._build_row_data(field, model_obj, company, raw_json)
            hier = hierarchy.get(company.id, {})
            row["parent_id"] = hier.get("parent_id")
            row["level"] = hier.get("level", 1)
            row["has_children"] = hier.get("has_children", False)
            row["child_ids"] = hier.get("child_ids", [])
            values.append(row)

        # Ordenar para que la tabla refleje la jerarquía: padre antes que hijos
        values.sort(key=lambda r: (r["level"], r.get("parent_id") or 0, r["company_id"]))

        comodel_name = field.comodel_name if field.type == "many2one" else None

        # Opciones de selection globales (idénticas para todas las compañías, se
        # calculan una sola vez aquí para evitar trabajo repetido en _build_row_data)
        selection_options = None
        if field.type == "selection":
            selection_options = (
                list(field.selection)
                if isinstance(field.selection, list)
                else [(k, str(v)) for k, v in field._description_selection(model_obj.env)]
            )
            # Limpiar las selection_options que _build_row_data pudo haber añadido
            for r in values:
                r.pop("selection_options", None)

        return {
            "values": values,
            "field_type": field.type,
            "comodel_name": comodel_name,
            "selection_options": selection_options,
        }

    @api.model
    def copy_value_to_children(self, res_model, res_id, field_name, source_company_id):
        """Propaga el valor del campo en ``source_company_id`` a todos sus hijos
        accesibles (recursivo hasta 3 niveles).

        Verifica que el usuario tenga acceso de escritura al modelo y que las
        compañías destino estén en ``self.env.companies``.

        :param source_company_id: ID de la compañía cuyo valor se va a propagar.
        :returns: dict con dos claves: ``updated`` (lista de company_ids actualizados)
                  y ``skipped`` (lista de company_ids omitidos).
        """
        self.env["ir.model.access"].check(res_model, "write")
        model_obj = self.env[res_model]
        field = model_obj._fields.get(field_name)

        if not field or not field.company_dependent:
            raise ValueError(f"El campo '{field_name}' en '{res_model}' no es company_dependent.")

        accessible_ids = set(self.env.companies.ids)
        if source_company_id not in accessible_ids:
            raise ValueError("No tiene acceso a la compañía origen.")

        raw_json = self._get_raw_json(model_obj._table, field_name, res_id)
        source_key = str(source_company_id)
        source_value = raw_json.get(source_key)  # puede ser None (no especificado)

        # Obtenemos el valor real que se va a propagar: si hay clave → ese valor;
        # si no hay clave → el fallback resuelto para esa compañía.
        if source_key in raw_json:
            value_to_copy = source_value
        else:
            source_company = self.env["res.company"].browse(source_company_id)
            model_with_company = model_obj.with_company(source_company)
            try:
                fallback_rec = field.get_company_dependent_fallback(model_with_company)
                fv = field.convert_to_write(fallback_rec, model_with_company)
                # Convertir a formato de columna para escribir en el JSON
                value_to_copy = field.convert_to_column(fv, model_with_company)
            except Exception:
                value_to_copy = None

        # Recorrer hijos recursivamente (máx 3 niveles desde el padre original)
        def _get_all_descendants(company, depth=0):
            if depth >= 2:  # profundidad máxima desde el primer hijo (0-indexed)
                return []
            descendants = []
            for child in company.child_ids:
                if child.id in accessible_ids:
                    descendants.append(child)
                    descendants.extend(_get_all_descendants(child, depth + 1))
            return descendants

        source_company_rec = self.env["res.company"].browse(source_company_id)
        targets = _get_all_descendants(source_company_rec)

        if not targets:
            return {"updated": [], "skipped": []}

        record = model_obj.browse(res_id)

        # Sanitize para many2one
        if field.type == "many2one":
            current_json = self._get_raw_json(model_obj._table, field_name, res_id)
            sanitized = {k: (None if v is False else v) for k, v in current_json.items()}
            if sanitized != current_json:
                self._write_raw_json(model_obj._table, field_name, res_id, sanitized)
                record.invalidate_recordset([field_name])

        updated = []
        skipped = []
        for target in targets:
            write_value = value_to_copy
            # Para Many2one, el value_to_copy almacenado en JSONB es el ID (int/None)
            # Necesitamos pasarlo al ORM en el formato correcto para write().
            if field.type == "many2one":
                write_val_orm = int(value_to_copy) if value_to_copy else False
            else:
                write_val_orm = value_to_copy

            # Usamos un savepoint por compañía destino para que un error de
            # company_crossover en una hija no aborte el resto del lote.
            try:
                with self.env.cr.savepoint():
                    record_with_company = record.with_company(target)
                    record_with_company.write({field_name: write_val_orm})

                    # Forzar la clave en el JSON si el valor coincide con el fallback
                    # (el ORM lo descartaría en ese caso)
                    current_json = self._get_raw_json(model_obj._table, field_name, res_id)
                    target_key = str(target.id)
                    if target_key not in current_json:
                        current_json[target_key] = write_value
                        self._write_raw_json(model_obj._table, field_name, res_id, current_json)
                        record.invalidate_recordset([field_name])

                updated.append(target.id)
            except (ValidationError, UserError) as exc:
                # Registrar la falla sin interrumpir el resto del lote.
                reason = exc.args[0] if exc.args else str(exc)
                # Limpiar etiquetas HTML básicas para el mensaje
                if hasattr(reason, "__html__"):
                    reason = str(reason)
                _logger.warning(
                    "copy_value_to_children: skip %s (id=%s) — %s",
                    target.name,
                    target.id,
                    reason,
                )
                skipped.append({"id": target.id, "name": target.name, "reason": str(reason)})

        return {"updated": updated, "skipped": skipped}

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

        Cada entrada se escribe en un savepoint individual: un error de
        company_crossover en una compañía no aborta las demás.

        :param values_dict: dict ``{str(company_id): value}`` donde *value* puede ser:
            - Un ID de registro (Many2one).
            - ``False``: guarda la clave como ``false`` en el JSON (vacío explícito).
            - ``"RESET"``: **elimina** la clave del JSON (restaura al fallback).
        :returns: dict con dos claves: ``saved`` (lista de company_ids guardados)
                  y ``skipped`` (lista de dicts {id, name, reason} que fallaron).
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

        saved = []
        skipped = []

        for company_id_str, value in values_dict.items():
            company_id = int(company_id_str)
            company = self.env["res.company"].browse(company_id)
            record_with_company = record.with_company(company)

            try:
                with self.env.cr.savepoint():
                    if value == "RESET":
                        # RESET: eliminar la clave de la compañía del JSONB.
                        fallback_rec = field.get_company_dependent_fallback(record_with_company)
                        write_val = field.convert_to_write(fallback_rec, record_with_company)
                        record_with_company.write({field_name: write_val})

                        raw_json = self._get_raw_json(model_obj._table, field_name, res_id)
                        if str(company_id) in raw_json:
                            del raw_json[str(company_id)]
                            self._write_raw_json(model_obj._table, field_name, res_id, raw_json)
                            record.invalidate_recordset([field_name])
                    else:
                        # Valor explícito (ID o False): ORM con with_company.
                        record_with_company.write({field_name: value})
                        # Forzar la clave si el ORM la descartó por coincidir con el fallback.
                        fallback_rec = field.get_company_dependent_fallback(record_with_company)
                        fallback_column = field.convert_to_column(
                            field.convert_to_write(fallback_rec, record_with_company),
                            record_with_company,
                        )
                        write_column = field.convert_to_column(value, record_with_company)
                        if write_column == fallback_column:
                            raw_json = self._get_raw_json(model_obj._table, field_name, res_id)
                            raw_json[str(company_id)] = write_column
                            self._write_raw_json(model_obj._table, field_name, res_id, raw_json)
                            record.invalidate_recordset([field_name])

                saved.append(company_id)
            except (ValidationError, UserError) as exc:
                reason = exc.args[0] if exc.args else str(exc)
                if hasattr(reason, "__html__"):
                    reason = str(reason)
                _logger.warning(
                    "set_company_dependent_values: skip company %s (id=%s) — %s",
                    company.name,
                    company_id,
                    reason,
                )
                skipped.append({"id": company_id, "name": company.name, "reason": str(reason)})

        return {"saved": saved, "skipped": skipped}

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
