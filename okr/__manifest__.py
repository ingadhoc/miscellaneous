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
'depends': ['base'],
'data': ['security/ir.model.access.csv',
        'data/kr_ppal_data.xml',
        'views/objetivo_line.xml',
        'views/objetivo.xml',
        'views/kr_ppal.xml',],
'application': True,
'installable': True,
'auto_install': False,
}
