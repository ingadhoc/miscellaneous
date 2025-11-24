{
'name': "OKR",
'version': "17.0.1.0.0",
'category': 'OKR',
'summary': "Gestión de OKR",
'license': 'LGPL-3',
'description': """
Gestión de OKR
""",
'author': "Pablo Montenegro",
'depends': ['base', 'hr'],
'data': ['data/ir_module_category_data.xml',
        'security/ir.model.access.csv',
        'views/okr_key_result.xml',
        'views/okr_objective.xml',
        'views/kr_ppal.xml',
        ],
'demo': [
        'demo/kr_ppal_data.xml',
    ],
'application': True,
'installable': True,
'auto_install': False,
}
