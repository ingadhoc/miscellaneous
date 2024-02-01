{
    'name': 'OKR',
    'description': """
        A module for Objectives and Key Results (OKR) management in Odoo.
    """,
    'version': "16.0.1.0.0",
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'depends': [
        'mail',
        'hr'
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'views/okr_objective.xml',
        'views/okr_result.xml',
        'views/menu.xml'
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False
}
