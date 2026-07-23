##############################################################################
#
#    Copyright (C) 2026  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
##############################################################################
{
    "name": "WhatsApp UX",
    "version": "19.0.1.1.0",
    "category": "WhatsApp",
    "sequence": 14,
    "summary": "One-click bulk send server action for every approved WhatsApp template",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "LGPL-3",
    "images": [],
    "depends": [
        "whatsapp",
    ],
    "data": [
        "views/whatsapp_template_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "demo": [
        "demo/whatsapp_ux_demo.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
