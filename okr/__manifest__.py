{
'name': "OKR",
'version': '16.0.1.0.0',
'category': 'OKR',
'summary': "Gestión de OKR",
'license': 'LGPL-3',
'description': """
Manage Library
==============
Description related to library.
""",
'author': "Pablo Montenegro",
'depends': ['base', 'hr'],
'data': ['data/ir_module_category_data.xml',
        'security/ir.model.access.csv',
        'data/kr_ppal_data.xml',
        'views/okr_key_result.xml',
        'views/okr_objective.xml',
        'views/kr_ppal.xml',],
'application': True,
'installable': True,
'auto_install': False,
}
