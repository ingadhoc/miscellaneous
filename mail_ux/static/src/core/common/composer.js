import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { toRaw } from "@odoo/owl";
import { isEventHandled } from "@web/core/utils/misc";

patch(Composer.prototype, {

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
    },
    async sendScheduleMessage() {
        const composer = toRaw(this.props.composer);
        if (composer.message) {
            this.editMessage();
            return;
        }
        await this.processMessage(async (value) => {
            await this._sendScheduleMessage(value, this.postData, this.extraData);
        });
    },
    async _sendScheduleMessage(value, postData, extraData) {
        if (!session.send_message_delay){
            return await this._sendMessage(value, postData, extraData);
        }

        const thread = toRaw(this.props.composer.thread);
        const postThread = toRaw(this.thread);
        if (postThread.model === "discuss.channel") {
            // feature of (optimistic) temp message
            return await this._sendMessage(value, postData, extraData);
        } else {
            postData.attachments = postData.attachments ? [...postData.attachments] : []; // to not lose them on composer clear
            const { attachments, parentId, mentionedChannels, mentionedPartners } = postData;
            const body = value;
            const params = await this.store.getMessagePostParams({ body, postData, thread: thread });
            const scheduledDate = new Date();
            scheduledDate.setSeconds(scheduledDate.getSeconds() + session.send_message_delay);

            const formattedScheduledDate = scheduledDate.toISOString().slice(0, 19).replace("T", " ");
            await this.orm.call("mail.scheduled.message", 'create', [
                {
                'attachment_ids': attachments.map(attachment => attachment.id),
                'author_id': user.partnerId,
                'body': params.post_data.body,
                'model': postThread.model,
                'res_id': postThread.id,
                'is_note': postData.isNote,
                'partner_ids': params.post_data.partner_ids || [],
                'scheduled_date': formattedScheduledDate,
                'notification_parameters': JSON.stringify(params.post_data),
                'subject':  postThread.name,
            }])
        }
    },
    /**
     * @override
     */
    onKeydown(ev) {
        const composer = toRaw(this.props.composer);
        if (ev.key === "Enter") {
            if (isEventHandled(ev, "NavigableList.select") || !this.state.active) {
                ev.preventDefault();
                return;
            }

            const shouldPost = this.props.mode === "extended" ? ev.ctrlKey : !ev.shiftKey;
            if (!shouldPost) {
                return;
            }
            ev.preventDefault();
            if (composer.message) {
                this.editMessage();
            } else {
                this.sendScheduleMessage();
            }
        } else {
            super.onKeydown(ev);
        }
    }
})
