{
    'name': 'Mail Internal',
    'version': "15.0.1.0.0",
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
        'data/mail_message_subtype_data.xml',
        'wizards/mail_compose_message_views.xml',
    ],
    'assets': {
        'web.assets.backend': [
            "/mail_internal/static/src/xml/mail_internal.xml"
        ],
        'web.assets_qweb': [
            "/mail_internal/static/src/xml/mail_internal.xml"
        ],
    },
    'installable': True,
    'application': False,
}
