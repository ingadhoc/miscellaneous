import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    /**
     * WhatsApp channels are never leavable natively, only unpinnable, and unpinning
     * is undone by the next incoming message. Any member but the owner (the backend
     * refuses the owner) can leave instead.
     */
    get canLeaveWhatsapp() {
        return Boolean(
            this.channel_type === "whatsapp" &&
                this.self_member_id &&
                this.store.self_partner &&
                this.whatsapp_owner_partner_id !== this.store.self_partner.id &&
                !this.canLeave
        );
    },
});
