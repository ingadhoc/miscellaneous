# -*- coding: utf-8 -*-
{
    'name': "Transifex Push",
    'summary': "Helper module to push translations to Transifex",
    'description': "Helper module to push translations to Transifex",
    'author': "ADHOC SA",
    'website': "http://runbot.odoo.com",
    'category': 'Website',
    'version': '15.0.1.0.0',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'wizard/base_export_language_views.xml',
    ],
    'post_init_hook': 'post_init',
}
