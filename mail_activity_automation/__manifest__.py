
{
    'name': 'Mail Activity Automation',
    'version': "17.0.1.0.0",
    'category': 'Communications',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'mail',
    ],
    'data': [
        'views/mail_activity_type_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
