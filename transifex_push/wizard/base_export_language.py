from odoo import models, fields
from transifex.api import transifex_api
from odoo.exceptions import UserError
from odoo.tools.translate import trans_export
import contextlib
import io
import logging

_logger = logging.getLogger(__name__)


class BaseLanguageExport(models.TransientModel):
    _inherit = "base.language.export"

    api_key = fields.Char(default='1/7dbfd1118bec5ef2dfac3528d8c5cea3dbd42164')
    organization_slug = fields.Char(default='adhoc')
    project_slug = fields.Char(default='odoo-18-0')

    def action_transifex_push(self):
        self.ensure_one()
        self._transifex_push(self.modules, self.api_key, self.organization_slug, self.project_slug)

    def _transifex_push(self, modules, api_key, organization_slug, project_slug):
        """ Metodo que revisa las builds y se fija los commits con cambios de la build, si lo mismos tienen configurado transifex
        entonces itera sobre modulos e idiomas para sincornizar traducciones.
        IMPORTANTE: los idiomas que se deseen deben configurarse manualmente en transifex
        A la hora de generar los .po tenemos 3 opciones:
        * llamar al a odoo
        * Usar click odoo https://pypi.org/project/click-odoo-contrib/#click-odoo-makepot-stable
        * Algo parecido a lo que hacía la oca https://github.com/ingadhoc/maintainer-quality-tools/blob/master/travis/travis_transifex.py#L152
        """
        def _get_language_content(lang_code, module):
            with contextlib.closing(io.BytesIO()) as buf:
                trans_export(lang_code, [module.name], buf, 'po', self._cr)
                content = buf.getvalue().decode("utf-8")
            return content

        _logger.info('Pushing translations to transifex')
        if not api_key or not organization_slug or not project_slug:
            raise UserError(
                'Se deben configurar los siguientes parametros de transfiex: api_key, organization_slug, project_slug')

        installed_langs = {x.iso_code: x.code for x in self.env['res.lang'].with_context(active_test=True).search([])}

        transifex_api.setup(auth=api_key)
        tx_organization = transifex_api.Organization.get(slug=organization_slug)
        tx_project = tx_organization.fetch('projects').get(slug=project_slug)

        tx_project_languages = {x.code: x.id for x in tx_project.fetch('languages').all()}
        po_format = transifex_api.i18n_formats.get(organization=tx_organization, name='PO')

        for module in modules:
            module_name = module.name
            try:
                # obtenemos el resource de esta manera ya que filter o get con slug o name no hacen busqueda exacta y si coincide
                # la primer parte nos devuelve varios resultados
                resource = transifex_api.resources.get('%s:r:%s' % (tx_project.id, module_name))
            except:
                attributes = {
                    "accept_translations": True,
                    "name": module_name,
                    "slug": module_name,
                }
                relationships = {
                    "i18n_format": po_format,
                    "project": tx_project,
                }
                _logger.info("Creating missing resource %s on transifex project %s", module_name, tx_project.name)
                resource = transifex_api.Resource.create(attributes=attributes, relationships=relationships)
            
            # subimos .pot (terminos en ingles)
            content = _get_language_content(False, module)
            res = transifex_api.resource_strings_async_uploads.upload(resource=resource, content=content)
            _logger.info('Result: %s', res)

            # subimos traducciones existentes
            for tx_language in tx_project_languages:
                if tx_language not in installed_langs.keys():
                    _logger.warning('Language %s not installed on database, skiping sync to transfiex', tx_language)
                    continue
                content = _get_language_content(installed_langs[tx_language], module)

                res = transifex_api.resource_translations_async_uploads.upload(
                    resource=resource, content=content, language=tx_project_languages[tx_language])
                _logger.info('Result: %s', res)
