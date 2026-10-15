import { ScheduledMessage } from "@mail/chatter/common/scheduled_message_model";
import { patch } from "@web/core/utils/patch";

patch(ScheduledMessage.prototype, {
    // The author can also cancel their own scheduled message
    get deletable() {
        return super.deletable || this.isSelfAuthored;
    },
});
