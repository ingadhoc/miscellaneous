odoo.define('mail_ux.chat_client_action_mobile', function (require) {
    "use strict";

    var chat_manager = require('mail.chat_manager');
    var core = require('web.core');
    var qweb = core.qweb;

    var ChatAction = core.action_registry.get('mail.chat.instant_messaging');
    ChatAction.include({
        update_message_on_current_channel: function (current_channel_id, message) {
            var starred = current_channel_id === "channel_starred" && !message.is_starred;
            var inbox = current_channel_id === "channel_inbox" && !message.is_needaction;
            var all = current_channel_id === "channel_all";
            var archive = current_channel_id === "channel_archive" && !message.is_archive;
            return starred || inbox || all || archive;
        },
        on_update_message: function (message) {
            var self = this;
            var current_channel_id = this.channel.id;
            if (this.update_message_on_current_channel(current_channel_id, message)) {
                chat_manager.get_messages({channel_id: this.channel.id, domain: this.domain}).then(function (messages) {
                    var options = self.get_thread_rendering_options(messages);
                    self.thread.remove_message_and_render(message.id, messages, options).then(function () {
                        self.update_button_status(messages.length === 0);
                    });
                });
            } else if (_.contains(message.channel_ids, current_channel_id)) {
                this.fetch_and_render_thread();
            }
        }
    });

    chat_manager.get_channel_array = function(msg){
        return [ msg.channel_ids, 'channel_inbox', 'channel_starred', 'channel_archive', 'channel_all'];
    };

    chat_manager.start = function () {
        chat_manager.start.call(this,name);

        chat_manager.add_channel({
            id: "channel_all",
            name: _lt("All"),
            type: "static",
        });
        chat_manager.add_channel({
            id: "channel_archive",
            name: _lt("Archive"),
            type: "static"
        });
    };

    var ChatClientAction = require('mail.chat_client_action_mobile');
    ChatAction.include({
        _isInInboxTab: function () {
            return _.contains(['channel_inbox', 'channel_starred', 'channel_all', 'channel_archive'], this.currentState);
        },

    });


    // chat_manager.get_channels = function () {
    //     return _.clone(channels);
    // };
    // chat_manager.get_channel = function (id) {
    //     return _.findWhere(channels, {id: id});
    // };

    // ChatManager.ChatManager.include({
    //     make_message: make_message,
    //     start: function () {
    //         return this._super.apply(this, arguments);
    //     },

    chat_manager.start();
    return chat_manager;
});
