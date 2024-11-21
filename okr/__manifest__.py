{
    'name': 'OKR',
    'version': "17.0.1.0.0",
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'depends': [
        'hr',
    ],
    'data': [
        'views/okr_objective_views.xml',
        'views/okr_key_result_views.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/okr_objective_demo.xml',
    ],
    'installable': True,
}
