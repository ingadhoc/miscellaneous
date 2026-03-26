##############################################################################
#
#    Copyright (C) 2025  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################
{
    "name": "Website LiveChat - Proveedor Externo",
    "version": "18.0.1.0.0",
    "category": "Website",
    "summary": "Integra un livechat de una instancia Odoo externa (ej: Odoo 19) en el website de Odoo 18",
    "description": """
        Permite incrustar el widget de livechat de una instancia Odoo de versión
        diferente (proveedor externo) en el website de esta instancia Odoo 18,
        evitando los conflictos de namespace JavaScript entre versiones.

        Utiliza un iframe aislado para que los globals de Odoo 19 (owl, odoo, etc.)
        no colisionen con los de Odoo 18.

        Configuración:
        - Website > Configuración > External LiveChat
        - Ingresar la URL del proveedor y el ID del canal
    """,
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "depends": [
        "website",
        "base_setup",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/website_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "website_livechat_external/static/src/js/external_livechat_service.js",
            "website_livechat_external/static/src/js/external_livechat_systray.js",
            "website_livechat_external/static/src/xml/external_livechat_systray.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
