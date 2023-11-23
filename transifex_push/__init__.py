
# from . import models
from . import wizard
from odoo import api, SUPERUSER_ID
import ast
import os
import logging

_logger = logging.getLogger(__name__)


def post_init(env):
    tx_data = ast.literal_eval(os.getenv('tx_data', '[]'))
    for api_key, organization_slug, project_slug, modules_names in tx_data:
        _logger.info('Pushing transifex translations for project %s-%s', organization_slug, project_slug)
        modules = env['ir.module.module'].search([('name', 'in', modules_names), ('state','=', 'installed')])
        env['base.language.export']._transifex_push(modules, api_key, organization_slug, project_slug)
