##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Odoo Integrator',
    'version': "16.0.1.0.0",
    'category': 'SaaS',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'depends': [
        'base', 'mail',
    ],
    # Lo estamos agregando a la imagen ??
    # 'external_dependencies': {
    #     'python': [
    #         'odooly',
    #     ],
    # },
    'data': [
        # 'data/mail_message_subtype_data.xml',
        'data/ir_server_action.xml',
        # 'data/mail_templates.xml',
        'security/integrator_security.xml',
        'security/ir.model.access.csv',
        'views/ir_ui_menuitem.xml',
        'views/integrator_account_views.xml',
        'views/integrator_integration_views.xml',
        'views/integrator_integration_script_views.xml',
        # 'data/log_cleaning_cron.xml',
        # 'data/integration_type_data.xml',
        # 'wizards/integrator_account_wizard_view.xml',
    ],
    # Este asset lo agregamos para poder usar html en las notificaciones usando el tag odumbo_notification
    # En versiones futuras revisar si sigue siendo necesario, si no pasar a display_notification
    # 'assets': {
    #     'web.assets_backend': [
    #         'integrator/static/src/webclient/actions/client_action.js',
    #     ]
    # },
    # Esto no lo agrego porque entiendo ya lo hacemos en repo de odooly
    # 'post_load': 'patch_odooly',
    'installable': True,
    'auto_install': False,
    'application': True,
    'demo': [
    ],
}
