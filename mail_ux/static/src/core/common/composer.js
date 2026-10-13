import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { toRaw } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },
    async _sendMessage(value, postData, extraData) {
        const thread = toRaw(this.thread);
        if (!session.send_message_delay || thread.channel) {
            return super._sendMessage(...arguments);
        }
        this.deleteSavedContent();
        const { post_data } = await this.store.getMessagePostParams({ body: value, postData, thread });
        const scheduledDate = new Date();
        scheduledDate.setSeconds(scheduledDate.getSeconds() + session.send_message_delay);
        await this.orm.call("mail.scheduled.message", "create", [
            {
                attachment_ids: post_data.attachment_ids || [],
                author_id: user.partnerId,
                body: post_data.body,
                model: thread.model,
                res_id: thread.id,
                is_note: postData.isNote,
                partner_ids: post_data.partner_ids || [],
                partner_cc_ids: post_data.partner_cc_ids || [],
                scheduled_date: scheduledDate.toISOString().slice(0, 19).replace("T", " "),
                notification_parameters: JSON.stringify(post_data),
                subject: post_data.subject || false,
            },
        ]);
        // Same cleanup as the native _sendMessage
        this.suggestion?.clearRawMentions();
        this.suggestion?.clearCannedResponses();
        this.props.composer.replyToMessage = undefined;
        this.props.composer.emailAddSignature = true;
        this.props.composer.thread.additionalRecipients = [];
    },
});
