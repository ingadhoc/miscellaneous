==========================
Base Company Dependent UX
==========================

Mejora la UX de los campos ``company_dependent`` en Odoo 19, replicando el
paradigma del *Asistente de Traducciones* (``fa-globe``), pero para valores
multicompañía.

.. contents::
   :local:

Problema que resuelve
=====================

En Odoo 18/19 los campos ``company_dependent`` ya no usan ``ir.property``; los
valores se almacenan como una columna JSONB dentro de la misma tabla del modelo
(ej. ``{"1": 45, "2": false}``). El ORM resuelve y devuelve el valor ya
computado para la compañía activa, por lo que el usuario desconoce si está
viendo:

* **Un valor específico** → clave ``company_id`` presente en el JSON.
* **El fallback global** → sin clave para esa compañía; se usa ``ir.default``.

Esto genera confusión al editar: el usuario puede modificar accidentalmente el
valor de *todas* las compañías (el default) pensando que solo toca la suya.

Adicionalmente, hay dos casos especiales donde el almacenamiento no es JSONB
directo:

* **Campos ``related``** (típicos en ``res.config.settings`` con
  ``related='company_id.xxx'``) → el valor real vive en ``res.company``.
* **Campos ``computed``/``inverse``** (ej. ``standard_price`` en
  ``product.template``, cuyo valor vive en ``product.product``).

El widget soporta los tres casos detectando automáticamente la estrategia.

Solución
========

Indicador visual en el formulario
----------------------------------

* **Ícono** ``fa-building-o`` a la derecha del campo, color **primario** (azul)
  cuando hay valor específico para la compañía activa, **gris** cuando es
  fallback.
* El texto del campo se renderiza en **gris/muted** cuando es el fallback.

Asistente multicompañía (Modal)
---------------------------------

Al pulsar el ícono se abre un diálogo con una tabla jerárquica (hasta 3
niveles: padre → hija → nieta) de todas las compañías accesibles para el
usuario (``env.companies``):

* **Editar** valores por compañía sin cambiar de sesión.
* **Reset** restaura el fallback global (elimina la clave del JSON).
* **Copy to children** propaga el valor de una compañía padre a sus hijas
  accesibles (salta las que no pasan validaciones de compañía).
* Indicadores visuales por nivel y badge ``Specific``/``Default``.

Diferencia clave Vaciar vs. Reset
''''''''''''''''''''''''''''''''''

+--------+------------------------------------+------------------+
| Acción | JSON resultante                    | Badge de estado  |
+========+====================================+==================+
| Vaciar | ``{"2": false}``                   | Específico       |
+--------+------------------------------------+------------------+
| Reset  | ``{}`` (clave eliminada)           | Por Defecto      |
+--------+------------------------------------+------------------+

**Reset en ORM-mode:** cuando el target real no es un campo JSONB nativo
(p. ej. una columna propia de ``res.company`` expuesta como ``related`` desde
``res.config.settings``) no hay clave que eliminar — cada compañía es su
propio registro. En esos casos *Reset* equivale a vaciar al falsy del tipo
(``False`` / ``0`` / ``""``); el badge "Por Defecto" sigue siendo informativo
pero no implica que el valor venga de un fallback global.

Tipos de campo soportados
==========================

El widget se inyecta automáticamente en los siguientes tipos de campo cuando
``company_dependent=True``:

* ``Many2one``
* ``Char``
* ``Integer``
* ``Float``
* ``Monetary``
* ``Boolean``
* ``Selection``
* ``Date`` / ``DateTime``

También aplica por *opt-in* explícito vía
``options="{'company_dependent_mode': 'orm'}"`` para campos computed/related
que exponen comportamiento company-dependent vía el ORM (sin columna JSONB).

Integración con ``res.config.settings``
========================================

El ícono ``fa-building-o`` que Odoo renderiza automáticamente en
``<setting company_dependent="1">`` se reemplaza por el botón interactivo del
widget. Funciona tanto cuando el campo es el primer hijo del ``<setting>``
(caso común) como cuando está envuelto en un ``<div>`` con ``<label>`` previo
(detección por DOM del primer campo visible).

Modo claro y oscuro
====================

Los estilos del diálogo usan variables CSS Bootstrap 5.3+ dark-aware
(``--bs-tertiary-bg``, ``--bs-secondary-bg``, ``--bs-emphasis-color-rgb``),
por lo que el contraste se mantiene correctamente en ambos temas.

Arquitectura técnica
====================

Backend (``base.company.dependent`` AbstractModel)
---------------------------------------------------

* ``get_company_dependent_values(res_model, res_id, field_name, mode=None)``
  → valores por compañía con jerarquía. ``mode`` auto-detecta ``'json'`` vs
  ``'orm'``.
* ``set_company_dependent_values(res_model, res_id, field_name, values_dict,
  mode=None)`` → escribe valores; soporta ``"RESET"`` para eliminar la clave
  del JSON.
* ``get_company_dependent_meta(res_model, res_id)``
  → ``{field_name: is_specific}`` en una sola query para todos los campos CD
  del modelo (incluye campos computed con ``depends_context('company')``).
* ``_detect_field_strategy(res_model, field_name)``
  → decide ``'json'`` (CD nativo + store) vs ``'orm'`` (computed/related
  vía ``with_company``).
* ``_resolve_orm_target(res_model, res_id, field_name)``
  → para campos no-JSON, resuelve al modelo/registro real donde escribir:

  * ``res.config.settings`` con ``related='company_id.xxx'`` →
    ``res.company`` directo.
  * ``product.template.standard_price`` con variante única →
    ``product.product``.

Frontend (OWL)
---------------

* **Servicio** ``company_dependent``: caché por registro, batching de RPCs
  ``get_company_dependent_meta`` para todos los campos CD de un formulario.
* **Patches** sobre ``Many2OneField``, ``CharField``, ``IntegerField``,
  ``FloatField``, ``MonetaryField``, ``BooleanField``, ``SelectionField``,
  ``DateTimeField`` (vía ``fields_patch.js``): inyectan
  ``CompanyDependentButton`` y aplican la clase ``o_cd_fallback``.
* **Patch** sobre ``Setting`` / ``SearchableSetting`` (``settings_patch.js``):
  reemplaza el icono estático por el botón interactivo en
  ``res.config.settings``.
* **``CompanyDependentButton``**: botón con tooltip dinámico, abre el
  diálogo.
* **``CompanyDependentDialog``**: tabla jerárquica con AutoComplete /
  SelectMenu / inputs según el tipo de campo, soporte de Copy-to-children
  y Reset.

Instalación
===========

.. code-block:: bash

   # Instalar desde la interfaz de Odoo o con:
   odoo-bin -d <db> -i base_company_dependent

Dependencias
============

* ``base``
* ``web``
* ``product``

Licencia
========

AGPL-3. Ver ``LICENSE`` para más detalles.
