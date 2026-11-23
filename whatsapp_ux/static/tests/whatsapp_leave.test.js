import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, defineModels, fields, serverState } from "@web/../tests/web_test_helpers";
import { whatsAppModels } from "@whatsapp/../tests/whatsapp_test_helpers";

class DiscussChannel extends whatsAppModels.DiscussChannel {
    whatsapp_owner_partner_id = fields.Many2one({ relation: "res.partner" });

    _to_store(store, fields) {
        super._to_store(...arguments);
        if (fields && Array.isArray(fields) && fields.length) {
            return;
        }
        const channels = this._filter([
            ["id", "in", this.map((channel) => channel.id)],
            ["channel_type", "=", "whatsapp"],
        ]);
        for (const channel of channels) {
            store._add_record_fields(this.browse(channel.id), {
                whatsapp_owner_partner_id: channel.whatsapp_owner_partner_id,
            });
        }
    }
}

describe.current.tags("desktop");
defineModels({ ...whatsAppModels, DiscussChannel });

async function openChatActions(name) {
    await click("[title='Chat Actions']", {
        parent: [".o-mail-DiscussSidebarChannel", { contains: ["span", { text: name }] }],
    });
}

test("a member that is not the owner can leave a whatsapp channel", async () => {
    const pyEnv = await startServer();
    const ownerPartnerId = pyEnv["res.partner"].create({ name: "Owner" });
    pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        whatsapp_owner_partner_id: ownerPartnerId,
        channel_member_ids: [
            Command.create({ partner_id: ownerPartnerId }),
            Command.create({ partner_id: serverState.partnerId }),
        ],
    });
    await start();
    await openDiscuss();
    await openChatActions("WhatsApp 1");
    await contains(".o-dropdown-item:contains('Unpin Conversation')");
    await click(".o-dropdown-item:contains('Leave Conversation')");
    // native prompt: the mock channel is created by the current user
    await click(".modal button", { text: "Leave Conversation" });
    await contains(".o-mail-DiscussSidebarChannel", {
        count: 0,
        contains: ["span", { text: "WhatsApp 1" }],
    });
});

test("the owner of a whatsapp channel can only unpin it", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        whatsapp_owner_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await openChatActions("WhatsApp 1");
    await contains(".o-dropdown-item:contains('Unpin Conversation')");
    await contains(".o-dropdown-item:contains('Leave Conversation')", { count: 0 });
});
