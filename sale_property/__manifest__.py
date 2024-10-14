{
    'name': 'sale_property',
    'version': "17.0.0.0.0",
    'category': '',
    'summary': 'Implements property fields to Sale Team and Sale Order models.',
    'description': """
    This module adds property fields to the Sale Team and Sale Order models.
    """,
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'depends': [ 
        'sale',
        'crm',
    ],
    'data':[
        'views/sale_order_views.xml'
    ],
    'demo':[

    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
