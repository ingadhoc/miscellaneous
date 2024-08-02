from odoo import models, tools, fields
from transifex.api import transifex_api
from odoo.exceptions import UserError
# import base64
import contextlib
import io
import logging

_logger = logging.getLogger(__name__)


class BaseLanguageExport(models.TransientModel):
    _inherit = "base.language.export"

    api_key = fields.Char(default='1/7dbfd1118bec5ef2dfac3528d8c5cea3dbd42164')
    organization_slug = fields.Char(default='adhoc')
    project_slug = fields.Char(default='odoo-16-0')

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
                tools.trans_export(lang_code, [module.name], buf, 'po', self._cr)
                content = buf.getvalue().decode("utf-8")
                #  y luego pasando "content_encoding": "text",

                # la otra alternativa es subirlo como base64 pero no sabemos como hacer con metodo "upload" (sincrono),
                # haciendo algo asi (y luego pasando "content_encoding": "base64",)
                # content = base64.encodebytes(buf.getvalue())

            # f = open(tmp_file)
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
            # asincrono (por ahora no usamos)))
            # upload = transifex_api.resource_strings_async_uploads.create(
            #     attributes={"content": content, "content_encoding": "text"}, relationships={"resource": resource})
            # # chequear estado (este codigo que sugiere no va pero si nos funcoona)
            # upload.attributes['status']
            # # cuando llegue a succeeded o sea distinto de "pending"
            # upload.reload()
            # si lo quisieramos hacer sincrono podemos hacerlo así, pero para que no tarde mucho, dejamos que se haga en back
            res = transifex_api.resource_strings_async_uploads.upload(resource=resource, content=content)
            _logger.info('Result: %s', res)

            # subimos traducciones existentes
            for tx_language in tx_project_languages:
                if tx_language not in installed_langs.keys():
                    _logger.warning('Language %s not installed on database, skiping sync to transfiex', tx_language)
                    continue
                content = _get_language_content(installed_langs[tx_language], module)
                # asincrono
                # upload = transifex_api.resource_translations_async_uploads.create(
                #     attributes={"content": content, "content_encoding": "text", "file_type": "default"},
                #     relationships={"resource": resource, 'language': tx_language,})
                # upload.attributes['status']
                # upload.reload()

                # sincrono
                res = transifex_api.resource_translations_async_uploads.upload(
                    resource=resource, content=content, language=tx_project_languages[tx_language])
                _logger.info('Result: %s', res)

        # Actualmente trabajamos leyendo los idiomas que existen en transifex, pero si se quisieran crear desde runbot
        # se podría ahcer algo asi
        # # CREAR IDIOMA EN PROYECTO SI NO EXISTE
        # language = transifex_api.Language.get(code="pt_BR")
        # languages = project.fetch('languages')
        # if language not in languages:
        #     project.add('languages', [language])
        #     project.save(translation_memory_fillup=True)
