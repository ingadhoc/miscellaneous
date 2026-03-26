/** @odoo-module */

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const externalLivechatService = {
    dependencies: [],

    async start() {
        const state = { available: false };

        let config;
        try {
            config = await rpc("/website_livechat_external/config", {});
        } catch {
            return state;
        }
        if (!config || !config.enabled) {
            return state;
        }

        state.available = true;

        const frame = document.createElement("iframe");
        frame.id = "external_livechat_frame_backend";
        frame.src = "/website_livechat_external/backend_frame";
        frame.style.cssText =
            "position:fixed;top:0;left:0;width:100%;height:100%;" +
            "border:none;z-index:2147483646;pointer-events:none;" +
            "background:transparent;";
        frame.setAttribute("allowtransparency", "true");
        frame.setAttribute("allow", "microphone; camera");
        frame.setAttribute("title", "LiveChat");
        frame.setAttribute("aria-hidden", "true");
        document.body.appendChild(frame);

        let iframeDoc = null;

        /**
         * Detecta si las coordenadas del cursor caen sobre un elemento
         * del widget de livechat usando elementFromPoint() sobre el
         * documento del iframe.
         */
        function isOverLivechat(cx, cy) {
            if (!iframeDoc) {
                return false;
            }
            try {
                const el = iframeDoc.elementFromPoint(cx, cy);
                if (
                    !el ||
                    el === iframeDoc.documentElement ||
                    el === iframeDoc.body
                ) {
                    return false;
                }
                let node = el;
                while (node && node.nodeType === 1 && node !== iframeDoc.body) {
                    const cls =
                        typeof node.className === "string"
                            ? node.className
                            : "";
                    const id = node.id || "";
                    if (
                        cls.toLowerCase().includes("livechat") ||
                        id.toLowerCase().includes("livechat")
                    ) {
                        return true;
                    }
                    node = node.parentElement;
                }
            } catch {
                /* cross-origin safety – ignore */
            }
            return false;
        }

        document.addEventListener("mousemove", (e) => {
            if (!iframeDoc) {
                return;
            }
            frame.style.pointerEvents = isOverLivechat(e.clientX, e.clientY)
                ? "auto"
                : "none";
        });

        frame.addEventListener("load", () => {
            try {
                iframeDoc =
                    frame.contentDocument ||
                    (frame.contentWindow && frame.contentWindow.document);
                if (iframeDoc) {
                    iframeDoc.addEventListener("mousemove", (e) => {
                        if (!isOverLivechat(e.clientX, e.clientY)) {
                            frame.style.pointerEvents = "none";
                        }
                    });
                }
            } catch (e) {
                console.warn(
                    "[ExternalLivechat] No se pudo acceder al DOM del iframe:",
                    e
                );
            }
        });

        /**
         * Envía un mensaje al iframe para que abra/cierre el livechat.
         * Usa postMessage porque el botón vive dentro de un shadow DOM
         * y no es accesible con querySelector desde el parent.
         */
        function openChat() {
            try {
                frame.contentWindow.postMessage(
                    { type: "toggle_livechat" },
                    window.location.origin
                );
                frame.style.pointerEvents = "auto";
            } catch (e) {
                console.warn("[ExternalLivechat] No se pudo abrir el chat:", e);
            }
        }

        state.openChat = openChat;
        return state;
    },
};

registry
    .category("services")
    .add("external_livechat_backend", externalLivechatService);
