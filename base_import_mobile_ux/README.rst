==========================
Base Import Mobile UX
==========================

Show the Import action in the gear menu on small screens

Características
===============

- Muestra la opción "Importar" en el menú de acciones (engranaje)
  de las vistas lista, kanban y grilla cuando la pantalla es chica (mobile),
  donde el core de Odoo la oculta por defecto.
- No cambia ningún otro criterio de visibilidad: sigue respetando el tipo de
  acción, el tipo de vista, y los atributos ``import``/``create`` del arch,
  tal como los define el core.

Detalles Técnicos
=================

- No agrega modelos nuevos ni hereda modelos existentes.
- ``static/src/import_records.js``: re-registra la entrada ``import-menu``
  del registry ``cogMenu`` (``registry.category("cogMenu")``), reutilizando
  ``importRecordsItem`` de ``base_import`` y repitiendo su condición
  ``isDisplayed`` sin el chequeo de pantalla chica.
- La condición se repite en vez de delegarse porque el core la evalúa contra
  el servicio ``ui`` y no contra el ``env`` que recibe. Si el core cambia esa
  condición, hay que acompañarla acá.

Uso
===

Con el módulo instalado, al abrir una vista lista, kanban o grilla desde una
pantalla angosta (mobile), el menú de acciones (ícono de engranaje) incluye la
opción "Importar" además de las que ya se mostraban.

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
