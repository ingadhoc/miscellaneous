{
    'name': 'OKR Management',
    'version': '17.0.1.0',
    'description': 'Module destined for Adhoc OKR Management',
    'author': 'Alexis Lopez',
    'license': 'LGPL-3',
    'depends': [
        'base','hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/okr_management.xml',
    ],
    'auto_install': False,
    'installable': True,
    'application': True,
}
