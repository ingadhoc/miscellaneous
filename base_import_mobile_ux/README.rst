==========================
Base Import Mobile UX
==========================

Show the Import action in the list view gear menu on small screens

Características
===============

- Muestra la opción "Importar registros" en el menú de acciones (engranaje)
  de la vista lista cuando la pantalla es chica (mobile), donde el core de
  Odoo la oculta por defecto.
- No cambia ningún otro criterio de visibilidad: sigue respetando el tipo de
  acción, el tipo de vista, y los atributos ``import``/``create`` del arch,
  tal como los define el core.

Detalles Técnicos
=================

- No agrega modelos nuevos ni hereda modelos existentes.
- ``static/src/import_records.js``: re-registra la entrada ``import-menu``
  del registry ``cogMenu`` (``registry.category("cogMenu")``), reutilizando
  ``importRecordsItem`` de ``base_import`` y forzando ``isSmall`` a ``false``
  al evaluar su condición ``isDisplayed``, sin duplicar el resto de la lógica
  original.

Uso
===

Con el módulo instalado, al abrir cualquier vista lista desde una pantalla
angosta (mobile), el menú de acciones (ícono de engranaje) incluye la opción
"Importar registros" además de las que ya se mostraban.

Arquitectura
============

Módulo puramente de frontend: un único asset JS cargado en
``web.assets_backend`` que sobreescribe una entrada del registry ``cogMenu``
del core. No tiene lógica Python, vistas ni datos.

Dependencias
============

- base_import

Autor
=====

ADHOC SA

Licencia
========

AGPL-3
