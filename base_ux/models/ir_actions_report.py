##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import base64
import logging
import re
from html import unescape
from urllib.parse import parse_qsl, unquote, urlsplit

from markupsafe import Markup
from odoo import models

_logger = logging.getLogger(__name__)

# <link type="text/css" rel="stylesheet" href="/web/assets/<unique>/<filename>.css"/>
ASSET_LINK_RE = re.compile(
    r"""<link\b[^>]*?\bhref=(?P<q>["'])"""
    r"""(?P<url>/web/assets/(?P<unique>[^/"']+)/(?P<filename>[^"']+?\.css))"""
    r"""(?P=q)[^>]*?>""",
    re.IGNORECASE,
)
# <img src="/report/barcode/QR/valor?width=87"/> o
# <img src="/report/barcode/?barcode_type=QR&amp;value=valor&amp;width=87"/>
BARCODE_SRC_RE = re.compile(
    r"""src=(?P<q>["'])(?P<url>/report/barcode/[^"']*)(?P=q)""",
    re.IGNORECASE,
)
BARCODE_PREFIX = "/report/barcode/"
FONT_FACE_RE = re.compile(r"@font-face\s*\{[^}]*\}", re.IGNORECASE)
CSS_URL_RE = re.compile(r"""url\(\s*["']?(?P<url>[^)"']+)""", re.IGNORECASE)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _prepare_html(self, html, report_model=False):
        """Heredado para que el html que recibe wkhtmltopdf no dependa de pedidos HTTP
        contra la propia instancia.

        wkhtmltopdf resuelve contra ``base_url`` (o sea, contra el mismo Odoo) los
        ``<link>`` de los assets del reporte y los ``<img>`` de los códigos de barras.
        Eso vuelve el render circular: el worker que atiende el pedido queda bloqueado
        esperando a wkhtmltopdf, y wkhtmltopdf necesita otro worker libre que le
        conteste. Con ``workers = 3``, tres renders concurrentes agotan los tres, nadie
        hace accept() y todo queda trabado hasta ``limit_time_real``; el liveness probe
        mata el container antes de que el watchdog libere los workers.

        Embebiendo los assets y los códigos de barras, un render no necesita más que su
        propio worker.
        """
        res = super()._prepare_html(html, report_model=report_model)
        # el core devuelve {} cuando no encuentra el layout
        if not isinstance(res, tuple) or not self._is_report_self_contained():
            return res
        bodies, res_ids, header, footer, specific_paperformat_args = res
        return (
            [self._inline_report_resources(body) for body in bodies],
            res_ids,
            self._inline_report_resources(header),
            self._inline_report_resources(footer),
            specific_paperformat_args,
        )

    def _is_report_self_contained(self):
        """Permite desactivar el embebido por parámetro de sistema."""
        param = self.env["ir.config_parameter"].sudo().get_param("base_ux.report_self_contained", "1")
        return param not in ("0", "False", "false", "")

    def _inline_report_resources(self, html):
        if not html:
            return html
        content = self._inline_report_asset_links(str(html))
        content = self._inline_report_barcodes(content)
        return Markup(content) if isinstance(html, Markup) else content

    # ------------------------------------------------------------
    # ASSETS
    # ------------------------------------------------------------

    def _inline_report_asset_links(self, content):
        def replace(match):
            css = self._get_report_asset_css(match.group("unique"), match.group("filename"))
            # "</style" dentro del css cortaría el tag; ante la duda dejamos el link
            if not css or "</style" in css.lower():
                return match.group(0)
            return '<style type="text/css">%s</style>' % self._strip_local_font_faces(css)

        return ASSET_LINK_RE.sub(replace, content)

    def _strip_local_font_faces(self, css):
        """Saca las reglas ``@font-face`` que apuntan a archivos de la propia instancia.

        Son exactamente las que volverían a meter un pedido HTTP contra nosotros mismos,
        que es lo que este embebido viene a sacar. Y no se pierde nada: medido sobre los
        logs de producción, wkhtmltopdf hoy no pide ni una de esas fuentes (solo los dos
        CSS), porque las resuelve del sistema de la imagen que lo corre. Las ``@font-face``
        que apuntan afuera (el CDN de Noto) quedan como estaban.
        """
        keep = []
        last = 0
        for match in FONT_FACE_RE.finditer(css):
            urls = CSS_URL_RE.findall(match.group(0))
            has_local = any(not url.startswith(("data:", "http://", "https://", "//")) for url in urls)
            if has_local:
                keep.append(css[last : match.start()])
                last = match.end()
        keep.append(css[last:])
        return "".join(keep)

    def _get_report_asset_css(self, unique, filename):
        """Contenido del bundle de assets al que apunta la url, o None si no se pudo
        resolver (en ese caso se deja el ``<link>`` como estaba)."""
        url = self.env["ir.asset"]._get_asset_bundle_url(filename, unique, {})
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("public", "=", True),
                    ("url", "=", url),
                    ("res_model", "=", "ir.ui.view"),
                    ("res_id", "=", 0),
                ],
                limit=1,
            )
        )
        if not attachment:
            attachment = self._generate_report_asset_attachment(filename)
        if not attachment or not attachment.raw:
            return None
        return attachment.raw.decode()

    def _generate_report_asset_attachment(self, filename):
        """Genera el bundle si todavía no existe. No es lo habitual (el webclient lo
        deja generado), y puede fallar si el cursor es de solo lectura."""
        try:
            bundle_name, rtl, asset_type, autoprefix = self.env["ir.asset"]._parse_bundle_name(filename, False)
            if asset_type != "css":
                return None
            bundle = self.env["ir.qweb"]._get_asset_bundle(
                bundle_name, css=True, js=False, rtl=rtl, autoprefix=autoprefix
            )
            if not bundle.stylesheets:
                return None
            return bundle.css()
        except Exception:
            _logger.warning("No se pudo generar el bundle %s para embeberlo en el reporte", filename, exc_info=True)
            return None

    # ------------------------------------------------------------
    # CODIGOS DE BARRAS
    # ------------------------------------------------------------

    def _inline_report_barcodes(self, content):
        def replace(match):
            data_uri = self._get_report_barcode_data_uri(match.group("url"))
            if not data_uri:
                return match.group(0)
            quote = match.group("q")
            return "src=%s%s%s" % (quote, data_uri, quote)

        return BARCODE_SRC_RE.sub(replace, content)

    def _get_report_barcode_data_uri(self, url):
        """Misma resolución que el controller ``/report/barcode``, pero en proceso."""
        try:
            parts = urlsplit(unescape(url))
            kwargs = dict(parse_qsl(parts.query))
            barcode_type = kwargs.pop("barcode_type", None)
            value = kwargs.pop("value", None)
            path = parts.path[len(BARCODE_PREFIX) :]
            if path:
                barcode_type, _sep, value = path.partition("/")
                value = unquote(value)
            if not barcode_type or not value:
                return None
            barcode = self.env["ir.actions.report"].barcode(barcode_type, value, **kwargs)
        except Exception:
            _logger.warning("No se pudo generar el código de barras %s para embeberlo en el reporte", url)
            return None
        return "data:image/png;base64,%s" % base64.b64encode(barcode).decode()
