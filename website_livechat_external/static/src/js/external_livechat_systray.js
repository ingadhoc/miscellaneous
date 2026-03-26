/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ExternalLivechatSystray extends Component {
    static template = "website_livechat_external.SystrayItem";
    static props = {};

    setup() {
        this.livechat = useState(useService("external_livechat_backend"));
    }

    onClick() {
        if (this.livechat.openChat) {
            this.livechat.openChat();
        }
    }
}

export const systrayItem = {
    Component: ExternalLivechatSystray,
};

registry
    .category("systray")
    .add("website_livechat_external.SystrayItem", systrayItem, {
        sequence: 100,
    });
