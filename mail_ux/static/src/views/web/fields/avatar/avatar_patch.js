import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { imageUrl } from "@web/core/utils/urls";

patch(Avatar.prototype, {
    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
    },

    /**
     * Builds the avatar image URL including a `unique` cache-buster when the
     * record's `write_date` is available in the mail store. This allows the
     * browser to cache avatars as immutable resources (up to 1 year), avoiding
     * a conditional HTTP request on every page load.
     *
     * Falls back to the plain URL (current Odoo behaviour) when `write_date`
     * is not yet known in the store.
     */
    get avatarSrc() {
        const { resModel, resId } = this.props;
        let writeDate;

        if (resModel === "res.users") {
            writeDate = this.store["res.users"].get(resId)?.partner_id?.write_date;
        } else if (resModel === "res.partner") {
            writeDate = this.store["res.partner"].get(resId)?.write_date;
        }

        if (writeDate) {
            return imageUrl(resModel, resId, "avatar_128", { unique: writeDate });
        }
        return `/web/image/${resModel}/${resId}/avatar_128`;
    },
});
