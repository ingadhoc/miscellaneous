{
    'name': 'Gestion OKR',
    'version': "16.0.1.0.0",
    'category': 'Base',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'depends': [
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/okr_objetive_views.xml',
        'views/okr_kr_views.xml',
        'views/okr_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
