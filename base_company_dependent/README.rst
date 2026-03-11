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

Solución
========

Se añade un **widget inteligente multicompañía** a todos los campos
``Many2one`` marcados con ``company_dependent=True``:

Indicador visual en el formulario
----------------------------------

* **Ícono** ``fa-building-o`` a la derecha del campo.

  * Color **primario** (azul) → valor específico para la compañía activa.
  * Color **gris** → valor por defecto/fallback.

* El texto del campo se renderiza en **gris/cursiva** cuando es el fallback.

Asistente multicompañía (Modal)
---------------------------------

Al pulsar el ícono se abre un diálogo con una tabla de todas las compañías
accesibles para el usuario (``env.companies``):

+------------+----------------------------------+---------------+------------------+
| Compañía   | Valor                            | Estado        | Acción           |
+============+==================================+===============+==================+
| Cía A      | Autocomplete Many2one            | Específico    | [\|Reset\|]      |
+------------+----------------------------------+---------------+------------------+
| Cía B      | (vacío)                          | Por Defecto   | [\|Reset\|] (×)  |
+------------+----------------------------------+---------------+------------------+

* **Vaciar** el Many2one guarda ``false`` en el JSON → campo vacío *explícito*
  (badge «Específico»).
* **Reset** *elimina* la clave del JSON → el campo vuelve al fallback global.

Diferencia clave Vaciar vs. Reset
''''''''''''''''''''''''''''''''''

+--------+------------------------------------+------------------+
| Acción | JSON resultante                    | Badge de estado  |
+========+====================================+==================+
| Vaciar | ``{"2": false}``                   | Específico       |
+--------+------------------------------------+------------------+
| Reset  | ``{}`` (clave eliminada)           | Por Defecto      |
+--------+------------------------------------+------------------+

Fase MVP (implementada)
========================

* Soporte para campos ``Many2one``.
* Indicador visual gris/color-primario.
* Modal funcional: listar, editar, resetear.
* Caché por formulario: una sola query SQL para todos los campos
  ``company_dependent`` del modelo.

Fase 2 (pendiente)
==================

* Soporte para campos ``Float`` e ``Integer``.
* Botón «Copiar a todas las compañías hijas».

Arquitectura técnica
====================

Backend
-------

``base.company.dependent`` (``models.AbstractModel``):

* ``get_company_dependent_values(res_model, res_id, field_name)``
  → valores crudos por compañía (para el modal).
* ``set_company_dependent_values(res_model, res_id, field_name, values_dict)``
  → escribe el JSON crudo (soporta ``RESET``).
* ``get_company_dependent_meta(res_model, res_id)``
  → ``{field_name: is_specific}`` en una sola query (para el indicador visual).

Frontend (OWL)
--------------

* **Servicio** ``company_dependent``: caché por registro, batching de RPCs.
* **Patch** ``Many2OneField``: carga meta en ``onWillStart``, inyecta el
  sub-componente y el template extendido.
* **``CompanyDependentButton``**: ícono con tooltip dinámico, abre el diálogo.
* **``CompanyDependentDialog``**: tabla interactiva con ``AutoComplete`` para
  Many2one y soporte de Reset.

Instalación
===========

.. code-block:: bash

   # Instalar desde la interfaz de Odoo o con:
   odoo-bin -d <db> -u base_company_dependent

Dependencias
============

* ``base``
* ``web``

Licencia
========

AGPL-3. Ver ``LICENSE`` para más detalles.
