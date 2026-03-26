import re

from odoo import http
from odoo.http import request

# Valida que la URL sea http/https con host válido, sin path (solo origen)
_VALID_ORIGIN_RE = re.compile(r"^https?://[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?(:\d+)?$")


class ExternalLivechatController(http.Controller):
    @http.route(
        "/website_livechat_external/config",
        type="json",
        auth="user",
    )
    def livechat_config(self):
        """Devuelve la configuración del livechat externo para el backend."""
        ICP = request.env["ir.config_parameter"].sudo()
        enabled = ICP.get_param("website_livechat_external.enabled", "False")
        return {
            "enabled": enabled in ("True", "1", "true"),
        }

    @http.route(
        "/website_livechat_external/frame",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def livechat_frame(self):
        """
        Devuelve una página HTML mínima y aislada que carga los scripts del
        livechat del proveedor externo (Odoo 19). Al servirse desde el mismo
        origen de Odoo 18, el iframe que la contiene puede manipular su DOM
        para habilitar pointer-events sólo sobre el widget del chat.
        """
        ICP = request.env["ir.config_parameter"].sudo()

        enabled = ICP.get_param("website_livechat_external.enabled", "False")
        if enabled not in ("True", "1", "true"):
            return request.not_found()

        provider_url = ICP.get_param("website_livechat_external.provider_url", "").rstrip("/")
        channel_id_raw = ICP.get_param("website_livechat_external.channel_id", "0")

        # Validaciones de seguridad básicas
        if not provider_url or not _VALID_ORIGIN_RE.match(provider_url):
            return request.make_response("URL del proveedor inválida.", status=400)

        try:
            channel_id = int(channel_id_raw)
            if channel_id <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return request.make_response("ID de canal inválido.", status=400)

        loader_src = f"{provider_url}/im_livechat/loader/{channel_id}"
        embed_src = f"{provider_url}/im_livechat/assets_embed.js"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            background: transparent;
            overflow: hidden;
        }}
    </style>
</head>
<body>
    <!--
        Esta página corre en su propio contexto JS (sin los globals de Odoo 18),
        por lo que los scripts de Odoo 19 no colisionan con los de Odoo 18.
    -->
    <script defer="defer" type="text/javascript" src="{loader_src}"></script>
    <script defer="defer" type="text/javascript" src="{embed_src}"></script>
    <script type="text/javascript">
        // Escucha mensajes del parent para abrir/cerrar el livechat.
        // El botón vive dentro de un shadow DOM (.o-livechat-root) y no es
        // accesible con querySelector desde el parent frame.
        window.addEventListener("message", function (ev) {{
            if (!ev.data || ev.data.type !== "toggle_livechat") return;
            var root = document.querySelector(".o-livechat-root");
            if (!root || !root.shadowRoot) return;
            var btn = root.shadowRoot.querySelector(".o-livechat-LivechatButton");
            if (btn) btn.click();
        }});
    </script>
</body>
</html>"""

        return request.make_response(
            html,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                # Solo permite embeber este frame desde el mismo origen
                ("X-Frame-Options", "SAMEORIGIN"),
            ],
        )

    @http.route(
        "/website_livechat_external/backend_frame",
        type="http",
        auth="user",
        sitemap=False,
    )
    def livechat_backend_frame(self):
        """
        Igual que livechat_frame pero sin website=True, para uso en el
        backend web client.
        """
        return self.livechat_frame()
