{
    'name': 'Mail Internal',
    'version': '13.0.1.0.0',
    'category': 'Communications',
    'sequence': 2,
    'summary': 'Internal Messaging',
    'author': 'ADHOC SA',
    'website': 'http://www.adhoc.com/ar',
    'license': 'AGPL-3',
    'depends': [
        'mail',
    ],
    'data': [
        'views/assets.xml',
        'data/mail_message_subtype_data.xml',
        'wizards/mail_compose_message_views.xml',
    ],
    'qweb': [
        'static/src/xml/mail_internal.xml',
    ],
    'installable': False,
    'application': False,
}
