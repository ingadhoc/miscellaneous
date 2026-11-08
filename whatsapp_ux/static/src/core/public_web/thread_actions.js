import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

// Next to the native "Unpin Conversation", which stays for the owner and for
// whoever just wants to hide the conversation for now.
registerThreadAction("whatsapp-leave", {
    condition: ({ owner, thread }) => thread?.canLeaveWhatsapp && !owner.isDiscussContent,
    icon: "fa fa-fw fa-sign-out",
    name: _t("Leave Conversation"),
    open: ({ thread }) => thread.leaveChannel(),
    partition: ({ owner }) => owner.env.inChatWindow,
    sequence: 11,
    sequenceGroup: 40,
    tags: ACTION_TAGS.DANGER,
});
