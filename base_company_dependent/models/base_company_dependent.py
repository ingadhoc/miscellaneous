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
    # Detección de estrategia (JSON directo vs ORM puro)
    # ------------------------------------------------------------------

    def _detect_field_strategy(self, res_model, field_name):
        """Determina si un campo debe usar lectura JSONB directa o ORM puro.

        :returns: ``'json'`` si el campo es un company_dependent nativo con
                  columna JSONB, ``'orm'`` si es computed/related/inverse que
                  expone datos company_dependent a través de la API ORM.
        """
        field = self.env[res_model]._fields.get(field_name)
        if not field:
            raise ValueError(f"El campo '{field_name}' no existe en '{res_model}'.")

        # Caso nativo: company_dependent + stored → JSONB directo
        if field.company_dependent and field.store:
            return "json"

        # Caso ORM: computed con depends_context('company')
        if "company" in (getattr(field, "depends_context", None) or ()):
            return "orm"

        # Caso related: seguir la cadena hasta el campo real
        if field.related:
            return self._detect_related_strategy(res_model, field)

        raise ValueError(
            f"El campo '{field_name}' en '{res_model}' no es company_dependent " f"ni depende del contexto de compañía."
        )

    def _detect_related_strategy(self, res_model, field):
        """Sigue la cadena ``related`` para detectar si el campo destino es CD."""
        related_parts = field.related.split(".")
        current_model = res_model
        for part in related_parts[:-1]:
            rel_field = self.env[current_model]._fields.get(part)
            if not rel_field:
                break
            if rel_field.type in ("many2one", "many2many", "one2many"):
                current_model = rel_field.comodel_name
            else:
                break
        final_field = self.env[current_model]._fields.get(related_parts[-1])
        if final_field and (
            final_field.company_dependent or "company" in (getattr(final_field, "depends_context", None) or ())
        ):
            return "orm"
        raise ValueError(f"El campo '{field.name}' en '{res_model}' no traza a un campo company_dependent.")

    def _resolve_orm_target(self, res_model, res_id, field_name):
        """Para campos computed/related, resuelve el modelo, campo y registro
        reales sobre los que operar con la estrategia ORM.

        Para ``res.config.settings`` con ``related='company_id.xxx'``, opera
        directamente sobre ``res.company``.

        Para ``product.template`` con ``standard_price`` (computed/inverse
        delegado a la variante), opera sobre ``product.product``.

        :returns: tupla ``(target_model, target_field_name, target_id)``
        """
        field = self.env[res_model]._fields.get(field_name)

        # Estrategia B: auto-detección para res.config.settings related fields
        if field.related:
            related_parts = field.related.split(".")
            if len(related_parts) == 2 and related_parts[0] == "company_id":
                # related='company_id.xxx' → operar sobre res.company
                real_field_name = related_parts[1]
                real_model = "res.company"
                real_id = self.env.company.id
                return real_model, real_field_name, real_id

            # Related genérico: seguir la cadena, pero solo a través de many2one.
            # Atravesar one2many/many2many devolvería un recordset multi y current.id
            # tomaría un registro arbitrario, lo que llevaría a leer/escribir el target
            # equivocado. Si la cadena no es traversable, caemos al fallback.
            record = self.env[res_model].browse(res_id)
            current = record
            traversable = True
            for part in related_parts[:-1]:
                rel_field = current._fields.get(part)
                if not rel_field or rel_field.type != "many2one":
                    traversable = False
                    break
                current = current[part]
            if traversable and current and len(current) == 1:
                return current._name, related_parts[-1], current.id

        # Computed/inverse: buscar si el campo existe como CD en un modelo
        # relacionado. Caso emblemático: product.template → product.product.
        # Verificamos que el res_id sea válido en el modelo destino antes de
        # recurrir — los IDs no son intercambiables entre modelos, así que solo
        # tiene sentido si el target apunta a un registro existente con ese id.
        if hasattr(field, "related_field") and field.related_field:
            target_model_name = field.related_field.model_name
            if self.env[target_model_name].browse(res_id).exists():
                return self._resolve_orm_target(
                    target_model_name,
                    res_id,
                    field.related_field.name,
                )

        # product.template.standard_price → product.product.standard_price
        # Con variante única delegamos a la variante para acceder al JSONB real de
        # product.product (is_specific exacto, valores precisos).
        # Con múltiples variantes el fallback mantiene el target en product.template:
        # la lectura devuelve el promedio vía computed y la escritura propaga a todas
        # las variantes vía _inverse — idéntico al comportamiento nativo de Odoo.
        if res_model == "product.template":
            template = self.env["product.template"].browse(res_id)
            variants = template.product_variant_ids
            if len(variants) == 1:
                variant_field = self.env["product.product"]._fields.get(field_name)
                if variant_field and variant_field.company_dependent:
                    return "product.product", field_name, variants.id

        # Fallback: usar el modelo/registro original con ORM puro
        return res_model, field_name, res_id

    # ------------------------------------------------------------------
    # Lectura ORM (sin JSONB)
    # ------------------------------------------------------------------

    def _build_row_data_orm(self, field, record, company):  # noqa: C901
        """Construye el dict de una fila usando lectura ORM pura (with_company).

        No accede a columnas JSONB; lee el valor a través del ORM estándar
        iterando por compañías con ``record.with_company(company)``.
        """
        rec = record.with_company(company)
        try:
            raw_val = rec[field.name]
        except Exception:
            raw_val = None

        # Obtener el valor de la compañía base (sin context) para comparar
        base_company = record.company_id if hasattr(record, "company_id") and record.company_id else self.env.company
        try:
            base_val = record.with_company(base_company)[field.name]
        except Exception:
            base_val = None

        value_id = None
        display_value = None
        fallback_value_id = None
        fallback_display_value = None
        selection_options = None

        if field.type == "many2one":
            value_id = raw_val.id if raw_val else None
            display_value = raw_val.display_name if raw_val else None
            fallback_value_id = base_val.id if base_val else None
            fallback_display_value = base_val.display_name if base_val else None

        elif field.type == "selection":
            selection_options = (
                list(field.selection)
                if isinstance(field.selection, list)
                else [(k, str(v)) for k, v in field._description_selection(rec.env)]
            )
            value_id = raw_val
            for key, label in selection_options:
                if key == raw_val:
                    display_value = str(label)
                    break
            if display_value is None and raw_val is not None:
                display_value = str(raw_val)
            fallback_value_id = base_val
            for key, label in selection_options:
                if key == base_val:
                    fallback_display_value = str(label)
                    break

        elif field.type in ("float", "integer", "monetary"):
            val = raw_val if raw_val is not False else None
            value_id = val
            display_value = str(val) if val is not None else ""
            fb = base_val if base_val is not False else None
            fallback_value_id = fb
            fallback_display_value = str(fb) if fb is not None else ""

        elif field.type == "boolean":
            value_id = bool(raw_val) if raw_val is not None else False
            display_value = str(value_id)
            fallback_value_id = bool(base_val) if base_val is not None else False
            fallback_display_value = str(fallback_value_id)

        elif field.type in ("char", "text"):
            value_id = raw_val
            display_value = raw_val or ""
            fallback_value_id = base_val
            fallback_display_value = base_val or ""

        elif field.type == "date":
            if hasattr(raw_val, "isoformat"):
                raw_val = raw_val.isoformat()
            value_id = raw_val
            display_value = raw_val
            fb = base_val
            if hasattr(fb, "isoformat"):
                fb = fb.isoformat()
            fallback_value_id = fb
            fallback_display_value = fb

        # Para ORM mode, usamos heurística para is_specific: comparamos con
        # la compañía base. Si difiere, lo consideramos específico.
        # Para el campo real subyacente, intentamos leer el JSONB si es posible.
        is_specific = self._check_orm_is_specific(record, field, company)

        row_domain = []
        if field.type == "many2one":
            comodel = self.env[field.comodel_name]
            static_domain = self._get_field_static_domain(field, rec)
            # Solo aplicar _check_company_domain cuando el comodelo tiene company_id
            # como campo propio. Si tiene company_ids (One2many) pero no company_id,
            # el default del ORM produce un dominio con company_id inválido.
            if "company_id" in comodel._fields:
                company_domain = Domain(comodel._check_company_domain(company))
                row_domain = list(static_domain & company_domain)
            else:
                row_domain = list(static_domain)

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

    def _check_orm_is_specific(self, record, field, company):
        """Determina si el valor del campo es específico para ``company``.

        Intenta resolver al campo CD subyacente para consultar el JSONB real.
        Si el subyacente no tiene columna JSONB (computed puro sin almacenamiento
        propio), devuelve ``False`` — el badge Specific/Default no es fiable en
        ese caso y un falso positivo es más dañino que un falso negativo.
        """
        try:
            target_model, target_field, target_id = self._resolve_orm_target(record._name, record.id, field.name)
            target_field_obj = self.env[target_model]._fields.get(target_field)
            if target_field_obj and target_field_obj.company_dependent and target_field_obj.store:
                raw_json = self._get_raw_json(self.env[target_model]._table, target_field, target_id)
                return str(company.id) in raw_json
        except (ValueError, Exception):
            pass

        # Computed puro sin JSONB: no se puede determinar is_specific sin ambigüedad.
        return False

    # ------------------------------------------------------------------
    # Escritura ORM (sin JSONB)
    # ------------------------------------------------------------------

    def _set_values_orm(self, res_model, res_id, field_name, values_dict):
        """Escribe valores por compañía usando ORM con with_company.

        Resuelve el target real (ej. res.company para settings, product.product
        para product.template) y escribe mediante el ORM estándar.

        ``RESET`` se traduce a ``write({field: False})`` — para targets ORM puros
        (ej. ``res.company`` columnas no-CD) no existe el concepto "remover
        override" del JSON path, por lo que reset == vaciar al falsy del tipo.
        Si el target resuelto sí es un campo CD nativo, este método delega al
        writer JSON donde RESET sí elimina la clave del JSONB.

        Access control: el método público que orquesta este path
        (``set_company_dependent_values``) chequea ``write`` sobre el
        ``res_model`` original; acá además chequeamos ``write`` sobre el
        ``target_model`` resuelto. Las cías del payload se filtran a
        ``self.env.companies`` para evitar escrituras cross-company por RPC.
        """
        target_model, target_field, target_id = self._resolve_orm_target(res_model, res_id, field_name)
        # Access control sobre el target resuelto (el público ya validó el res_model
        # original; acá cerramos el segundo modelo cuando el resolver salta de
        # res.config.settings a res.company / product.product / etc.).
        self.env["ir.model.access"].check(target_model, "write")
        _logger.debug(
            "[CD ORM SET] res_model=%s res_id=%s field=%s → target=(%s, %s, %s) values=%s",
            res_model,
            res_id,
            field_name,
            target_model,
            target_field,
            target_id,
            values_dict,
        )

        target_field_obj = self.env[target_model]._fields.get(target_field)
        record = self.env[target_model].browse(target_id)

        # Si el target resuelto es un campo CD nativo, delegamos al writer
        # JSON original que tiene mejor manejo de fallbacks y sanitización.
        if target_field_obj and target_field_obj.company_dependent and target_field_obj.store:
            _logger.debug("[CD ORM SET] delegating to JSON writer (target field is CD native)")
            return self.set_company_dependent_values(target_model, target_id, target_field, values_dict)

        # Filtrar a las cías accesibles para el usuario: un RPC malicioso podría
        # incluir IDs fuera de env.companies; los descartamos antes de escribir.
        accessible_ids = set(self.env.companies.ids)

        # Escritura ORM pura
        saved = []
        skipped = []

        for company_id_str, value in values_dict.items():
            company_id = int(company_id_str)
            company = self.env["res.company"].browse(company_id)
            if company_id not in accessible_ids:
                # Defensive skip: a malicious RPC payload listed a company the
                # caller cannot access. Info-level — the structured `skipped`
                # list below is what callers should consume; a WARNING here
                # breaks runbot's strict-warning policy on the Adhoc CI.
                _logger.info(
                    "_set_values_orm: skip company id=%s — not in env.companies",
                    company_id,
                )
                skipped.append({"id": company_id, "name": company.name or "", "reason": "no access to company"})
                continue

            try:
                with self.env.cr.savepoint():
                    # Para res.company cada compañía ES un registro distinto;
                    # with_company no cambia el record.id, solo el contexto.
                    if target_model == "res.company":
                        rec = self.env["res.company"].browse(company_id)
                    else:
                        rec = record.with_company(company)
                    write_value = False if value == "RESET" else value
                    before = rec[target_field]
                    rec.write({target_field: write_value})
                    after = rec[target_field]
                    _logger.debug(
                        "[CD ORM SET] wrote company=%s rec=%s.%s=%s (before=%r after=%r)",
                        company.name,
                        rec._name,
                        rec.id,
                        write_value,
                        before,
                        after,
                    )
                saved.append(company_id)
            except (ValidationError, UserError) as exc:
                reason = exc.args[0] if exc.args else str(exc)
                if hasattr(reason, "__html__"):
                    reason = str(reason)
                _logger.warning(
                    "set_values_orm: skip company %s (id=%s) — %s",
                    company.name,
                    company_id,
                    reason,
                )
                skipped.append({"id": company_id, "name": company.name, "reason": str(reason)})

        return {"saved": saved, "skipped": skipped}

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
            if "company_id" in comodel._fields:
                company_domain = Domain(comodel._check_company_domain(company))
                row_domain = list(static_domain & company_domain)
            else:
                row_domain = list(static_domain)

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
    def get_company_dependent_values(self, res_model, res_id, field_name, mode=None):
        """Retorna los valores por compañía para un campo company_dependent.

        Solo se incluyen las compañías a las que el usuario tiene acceso
        (``self.env.companies``). Incluye metadatos de jerarquía para el diálogo.

        :param res_model: Nombre técnico del modelo (ej. 'product.category').
        :param res_id: ID del registro.
        :param field_name: Nombre técnico del campo.
        :param mode: ``'json'``, ``'orm'`` o ``None`` (auto-detectar).
        :returns: dict con claves:
            - ``values``: lista de dicts por compañía con datos de jerarquía.
            - ``field_type``: 'many2one', 'selection', 'float', 'integer', etc.
            - ``comodel_name``: modelo del Many2one (solo si aplica).
            - ``selection_options``: lista [(key, label)] (solo si selection).
        """
        if mode is None:
            mode = self._detect_field_strategy(res_model, field_name)

        if mode == "orm":
            return self._get_values_orm(res_model, res_id, field_name)

        return self._get_values_json(res_model, res_id, field_name)

    def _get_values_json(self, res_model, res_id, field_name):
        """Implementación JSONB directa del getter de valores por compañía."""
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

    def _get_values_orm(self, res_model, res_id, field_name):
        """Implementación ORM pura del getter de valores por compañía.

        Resuelve el target real (ej. ``res.company`` para settings,
        ``product.product`` para template) y lee valores con ``with_company``.
        """
        self.env["ir.model.access"].check(res_model, "read")
        model_obj = self.env[res_model]
        model_obj.browse(res_id).check_access("read")
        field = model_obj._fields.get(field_name)
        if not field:
            raise ValueError(f"El campo '{field_name}' no existe en '{res_model}'.")

        # Resolver target real para lectura
        target_model, target_field, target_id = self._resolve_orm_target(res_model, res_id, field_name)
        _logger.debug(
            "[CD ORM GET] res_model=%s res_id=%s field=%s → target=(%s, %s, %s)",
            res_model,
            res_id,
            field_name,
            target_model,
            target_field,
            target_id,
        )
        target_field_obj = self.env[target_model]._fields.get(target_field)
        target_record = self.env[target_model].browse(target_id)

        # Si el target tiene JSONB nativo, delegamos la lectura al path JSON
        if target_field_obj and target_field_obj.company_dependent and target_field_obj.store:
            return self._get_values_json(target_model, target_id, target_field)

        # Lectura ORM pura
        hierarchy = {h["id"]: h for h in self._get_accessible_companies_hierarchy()}

        values = []
        for company in self.env.companies:
            # Para res.company cada compañía es su propio registro; no se puede
            # usar with_company sobre un registro fijo porque los campos normales
            # (no company_dependent) no varían por contexto sino por record.id.
            if target_model == "res.company":
                record_for_company = self.env["res.company"].browse(company.id)
            else:
                record_for_company = target_record
            _logger.debug(
                "[CD ORM GET] reading for company=%s record=%s.%s → %r",
                company.name,
                record_for_company._name,
                record_for_company.id,
                record_for_company.with_company(company)[target_field],
            )
            row = self._build_row_data_orm(target_field_obj, record_for_company, company)
            hier = hierarchy.get(company.id, {})
            row["parent_id"] = hier.get("parent_id")
            row["level"] = hier.get("level", 1)
            row["has_children"] = hier.get("has_children", False)
            row["child_ids"] = hier.get("child_ids", [])
            values.append(row)

        values.sort(key=lambda r: (r["level"], r.get("parent_id") or 0, r["company_id"]))

        comodel_name = target_field_obj.comodel_name if target_field_obj.type == "many2one" else None

        selection_options = None
        if target_field_obj.type == "selection":
            selection_options = (
                list(target_field_obj.selection)
                if isinstance(target_field_obj.selection, list)
                else [(k, str(v)) for k, v in target_field_obj._description_selection(model_obj.env)]
            )
            for r in values:
                r.pop("selection_options", None)

        return {
            "values": values,
            "field_type": target_field_obj.type,
            "comodel_name": comodel_name,
            "selection_options": selection_options,
        }

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
        if "company_id" in comodel._fields:
            company_domain = Domain(comodel._check_company_domain(company))
            effective = static_domain & company_domain
        else:
            effective = static_domain
        return list(effective)

    @api.model
    def set_company_dependent_values(self, res_model, res_id, field_name, values_dict, mode=None):
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
        :param mode: ``'json'``, ``'orm'`` o ``None`` (auto-detectar).
        :returns: dict con dos claves: ``saved`` (lista de company_ids guardados)
                  y ``skipped`` (lista de dicts {id, name, reason} que fallaron).
        """
        if mode is None:
            try:
                mode = self._detect_field_strategy(res_model, field_name)
            except ValueError:
                mode = "json"

        # Access control aplicado a ambos paths (json y orm).  El path orm,
        # además, valida write sobre el target_model resuelto dentro de
        # _set_values_orm — la cadena res.config.settings → res.company
        # cruza el chequeo dos veces.
        self.env["ir.model.access"].check(res_model, "write")

        if mode == "orm":
            return self._set_values_orm(res_model, res_id, field_name, values_dict)
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
        También detecta campos ORM-mode (computed con depends_context('company'))
        y los incluye usando heurística.
        """
        self.env["ir.model.access"].check(res_model, "read")
        model_obj = self.env[res_model]
        company_key = str(self.env.company.id)
        result = {}

        # Campos CD nativos (JSONB)
        cd_fields = [name for name, f in model_obj._fields.items() if f.company_dependent and f.store]
        if cd_fields:
            self.env.cr.execute(
                sql.SQL("SELECT {cols} FROM {table} WHERE id = %s").format(
                    cols=sql.SQL(", ").join(sql.Identifier(f) for f in cd_fields),
                    table=sql.Identifier(model_obj._table),
                ),
                (res_id,),
            )
            row = self.env.cr.fetchone()
            if row:
                result.update({field_name: (company_key in (row[i] or {})) for i, field_name in enumerate(cd_fields)})

        # Campos ORM-mode: computed con depends_context('company')
        for name, f in model_obj._fields.items():
            if name in result:
                continue
            depends_ctx = getattr(f, "depends_context", None) or ()
            if "company" not in depends_ctx:
                continue
            try:
                record = model_obj.browse(res_id)
                result[name] = self._check_orm_is_specific(record, f, self.env.company)
            except Exception:
                pass

        return result
