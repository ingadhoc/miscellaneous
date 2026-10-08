# Migración de código: base_company_dependent 19.0 → 20.0

## Resumen
Migrado con 2 puntos a revisar (M1 y M2) y sin bloqueantes. Instala en una base 20 limpia, pasan 40 tests de Python y la prueba de UI sobre un campo Char company_dependent anduvo. El frontend sigue sin red de tests JS: se siguió así con el OK de rov.

## Automático (migrator y upgrade_code)
- **Migrator de OCA: no corrido.** El fork instalado no acepta 19.0 como `--init-version-name` (sus opciones llegan hasta 18.0) y no tiene `migrate_190_200.py`. La inicialización se hizo a mano, con la misma convención del repo (`[MIG] pot_github_push`, b891c4c): versión `20.0.1.0.0` e `installable: True`.
- **upgrade_code `owl3-migration`:** tocó `company_dependent_dialog.js`, `fields_patch.js` y `templates.xml`:
  - `useState` → `proxy`;
  - `useService("notification")` → `usePlugin(NotificationPlugin)`;
  - `this.` en las plantillas;
  - `t-esc` → `t-out`;
  - `t-ref` → `t-custom-ref`, revertido a mano (ver abajo).
  - El primer pase perdió el cambio de `t-esc`. Con un segundo pase se aplicó, y un tercero ya no dejó diff.
- **`t-call`, `base64-in-xml`, `ormcache-on-transaction`, `tuple-rec_names_search`:** corridos en seco, sin cambios.
- **`ir-access`: no aplica.** El módulo no tiene archivos de permisos (`data: []`). Además, el script se cae por un manifiesto de otro módulo del repo (`account_statement_import_file`).
- **Catálogo:** se corrió con `--sin-catalogo` y se consultó `major.version.change` 20.0 por Tuqui (campos y modelos de `res.company`, `res.partner`, `ir.model.access` e `ir.default`). Hay 61 registros, de los que aplican dos: la baja del modelo `ir.model.access` (6012) y la de sus campos `perm_*`/`group_id` (5672–5677). Los dos quedaron resueltos.

## Resuelto agénticamente
- **`ir.model.access.check(model, op)` → `env[model].browse().check_access(op)`** (4 lugares en `models/base_company_dependent.py`). Evidencia: en 19 está `IrModelAccess.check` en `odoo/addons/base/models/ir_model.py`. En 20 el modelo no existe: lo reemplaza `ir.access` (`odoo/addons/base/models/ir_access.py`), y el chequeo a nivel modelo es `check_access` sobre un recordset vacío (`odoo/orm/models.py:3443`).
- **Refs de las plantillas copiadas:** `t-custom-ref="input"` → `t-ref="this.input"` y `t-custom-ref="numpadDecimal"` → `t-ref="this.numpadDecimalRef"`. Evidencia: en 19 era `t-ref="input"` / `t-ref="numpadDecimal"` (`web/static/src/views/fields/{char,integer,float,monetary}/*_field.xml`). En 20 es `input = signal.ref()` (char_field.js:27) y `numpadDecimalRef = signal.ref()` (float_field.js:27, integer_field.js:26). En 20 no hay directiva `t-custom-ref`. Sin este cambio el input no se conecta con `useInputField` y el valor no se guarda.
- **Plantillas resincronizadas con 20:**
  - Selection: `menuClass` sin `w-auto` y prop `required`.
  - Boolean: `displayAsToggle`.
  - Char: `TranslationButton` con `t-if` y el botón de placeholder con `data-icon="wand_stars"`.
  - Evidencia: el diff de `web/static/src/views/fields/*/*.xml` entre 19 y 20.
- **DateTime:** el xpath pasó de `//div[@t-ref='root']` a `//div[@t-ref='this.rootRef']`, y su contenido lleva `this.`. Evidencia: `datetime_field.xml:5` en 19 (`t-ref="root"`) contra 20 (`t-ref="this.rootRef"`).
- **`static props` → `props = useProps({...})`**, en `CompanyDependentButton` y `CompanyDependentDialog`. Evidencia: `owl3_compatibility_layer.js:44` de 20 tira error con `static props`, y Owl 3 no asigna `this.props` sin `useProps`. El core usa el mismo patrón (`translation_components.js`, `TranslationDialog`).
- **FontAwesome → Material Symbols** (`oi` + `data-icon`, todos de `icons_wishlist.txt`): business, autorenew + `oi-spin`, subdirectory_arrow_right, lock, public, content_copy, undo, save y wand_stars. Se ajustó también el selector `.o_cd_btn .fa` del CSS. Evidencia: en 20 FontAwesome no se carga.
- **Tests:**
  - El ACL del modelo de prueba pasó de `ir.model.access` sin grupo a `ir.access` con `base.group_user` y `operation: crud`. En 20, un `ir.access` sin grupo es una restricción (`ir_access.py:129`).
  - Se sacó una llamada redundante a `_reflect_models`, porque `init_models` ya refleja el modelo. En 20 rompía con `'Registry' object has no attribute '_post_init_queue'`.
- **Textos:** se sacaron del README las menciones a Odoo 19 y a los íconos de FontAwesome, se corrigió un comentario de `fields_patch.js` y se puso 20.0 en el encabezado del `.po`.

## Revisión adversarial
Hecha por un agente revisor de solo lectura. No hay bloqueantes en el módulo.
- **M1, a revisar, del salto:** el frontend no tiene red. Los 40 tests son de Python; la UI se probó solo con Char. Quedan sin ejecutar las otras 7 plantillas y el Guardar del diálogo, que usa `usePlugin(NotificationPlugin)`. Los tests `test_access_check_*` corren como superusuario y no ejercitan `check_access`.
- **M2, a revisar, del salto:** en 20, `BooleanToggleField` ya no tiene plantilla propia y hereda la de Boolean. Por eso el botón aparece también en los toggles. Ejemplo: `receipt_reminder_email` pasa a `widget="boolean_toggle"` en `purchase/views/res_partner_views.xml:11`. En una lista sería un botón por fila. Se infiere del código y no se vio en la UI.
- **M3, menor, sospecha:** las subclases de widgets sin plantilla propia que copian `static components` antes de que se cargue `fields_patch.js` (por ejemplo `Many2OneBankField`) podrían quedar sin `CompanyDependentButton`. Depende del orden de los assets y no se verificó.
- **M4, menor, del salto:** con un modelo inexistente, el error ahora es `KeyError` en vez de `AccessError`.
- **M5, menor:** textos viejos. **Corregido** en este commit.
- **M6, menor, preexistente:** `get_company_dependent_meta` controla el acceso al modelo pero no al registro.
- **De la herramienta, no del módulo; se sube al programa:**
  - R1: `owl3-migration` pierde cambios entre sus propios pasos. Cinco pasos releen el disco y pisan lo anterior.
  - R2: `t-ref` → `t-custom-ref` (y probablemente `t-model` → `t-custom-model`) genera directivas que en 20 no existen.

## Requiere revisión humana
- M2: **decidido por rov: se acepta un botón por fila.** Lo cubre un test JS (toggle en formulario y lista).
- M3: **confirmado y corregido.** En una base con `account`, `many2one_banks.js` carga antes que `fields_patch.js` (posiciones 2366 y 2462 del bundle), así que `Many2OneBankField` se queda con una copia de `components` sin el botón, pero hereda la plantilla parcheada. Están en la misma situación `NonFocusableSelectionField` (account_peppol) y `Many2OneBankPartnerField` (hr_payroll). En el estándar ninguno se usa sobre un campo company_dependent: el riesgo es latente. Arreglo: `addButtonToFieldSubclasses()` en `fields_patch.js` recorre el registro de campos y agrega el botón a esas subclases. Tiene test JS.
- M1: **tests JS agregados** (`static/tests/base_company_dependent.test.js`, Hoot): el botón en los 8 tipos, fallback/específico, guardado de un Char, toggle, lista, diálogo (guardar, copiar a hijas, reset, compañías omitidas) y M3. **No corridos en local:** el container no tiene Chrome. Los corre el runbot (`WebSuite.test_unit_desktop`, cruzado por módulo).

## Bloqueantes
- Ninguno.

## Migración de data
- ¿Hace falta script? **No.** Respondió rov. Motivo: el módulo no tiene campos guardados propios (sus dos modelos son abstractos) ni datos; los cambios son solo de API y frontend.

## Candidatos a gestión del cambio
- **Ícono del botón por compañía**
  - qué cambia: el ícono del botón que aparece junto a los campos por compañía pasa del edificio de FontAwesome al ícono "business" de Material Symbols; el comportamiento es el mismo.
  - a quién afecta: usuarios de bases multicompañía; el módulo está en 218 bases productivas.
  - por qué importa: solo cambia la apariencia.
- **El botón aparece en los campos con interruptor (M2)**
  - qué cambia: en 20, los campos por compañía que se muestran como interruptor (por ejemplo el recordatorio de recepción del proveedor) también muestran el botón, y en las listas aparecería en cada fila.
  - a quién afecta: usuarios de compras en bases multicompañía; de las 218 bases con el módulo, las que tienen compras instaladas: no sé cuántas.
  - por qué importa: no sé (depende de lo que se decida en M2).

## Verificación
- chequeo estático: ok (sintaxis Python, XML; 0 avisos de 20)
- pre-commit: pasó (ruff, ruff-format, pylint-odoo, xml, po, rstcheck)
- manifest version / installable: 20.0.1.0.0 / True
- intención (pre-flight): AMBIGUO → rov decidió MIGRAR. La tarea 76423 no tiene descripción; el estado en 20.0 es Migrando. Es el paso 1 de la agrupadora 76959.
- qué cambió (paso 0): `ir.model.access` → `ir.access` (lo usa el módulo en 4 chequeos y en un test); Owl 3 (signal refs, `useProps`, `proxy`, plugins) en las 8 plantillas y en los 2 componentes; FontAwesome dado de baja. Fuente: wiki-ia 19→20 del 2026-09-28 (usabilidad/base, transversal/web), confirmada contra el código de oba-20 (odoo `eadb3acd`).
- qué espera destino (paso 0b): nada en destino espera algo del módulo. Solo `account_multicompany_ux` lo tiene en `depends`, sin extenderlo.
- red de tests (paso 0c): 40 tests de Python con asserts; el frontend, sin red de JS. Se siguió con el OK de rov.
- base 20 local: instaló en `20.0-mig-base_company_dependent`. Tests del módulo: 40 ok, 0 fallas. UI: prueba con Chrome por CDP sobre `res.partner.barcode`: botón con ícono, clase de valor por defecto, valor guardado `BC-UI-1` y diálogo abierto. Capturas en el scratchpad de la sesión (01-form-fallback.png, 02-dialog.png).
- licencia (paso 4c): AGPL-3, sin cambios: no alcanza a Enterprise.
- traducciones (paso 4d):
  - Export con `--force-sync` y 13 términos traducidos.
  - `--force-sync` vació "The field '%s' is required…", aunque no lo avisó: se restauró la redacción anterior.
  - Quedan sin traducir, por estar en español: la descripción (README), el resumen y "Helpers para campos company_dependent".
- base real post-ODU: sin base para el par 19→20. Runbot todavía no corre el salto a 20 (tarea 77184), así que no se probó sobre una base real.
