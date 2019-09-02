odoo.define('mail_internal.ChatterComposer', function (require) {
    "use strict";

    var utils = require('mail.utils');
    var ChatterComposer = require('mail.composer.Chatter');

    var ChatterComposerInternal = ChatterComposer.include({
        _preprocessMessage: function () {
            var self = this;
            var def = $.Deferred();
            this._super().then(function (message) {
                message = _.extend(message, {
                    subtype: 'mail.mt_comment',
                    message_type: 'comment',
                    content_subtype: 'html',
                    context: self.context,
                });

                // Subtype
                if (self.options.isLog) {
                    message.subtype = 'mail.mt_note';
                }
                if (self.options.isInternal) {
                    message.subtype = 'mail_internal.mt_internal_message';
                }

                // Partner_ids
                if (!self.options.isLog && !self.options.isInternal) {
                    var checkedSuggestedPartners = self._getCheckedSuggestedPartners();
                    self._checkSuggestedPartners(checkedSuggestedPartners).done(function (partner_ids) {
                        message.partner_ids = (message.partner_ids || []).concat(partner_ids);
                        // update context
                        message.context = _.defaults({}, message.context, {
                            mail_post_autofollow: true,
                        });
                        def.resolve(message);
                    });
                } else {
                    def.resolve(message);
                }

            });

            return def;
        },
        _onOpenFullComposer: function () {
            if (!this._doCheckAttachmentUpload()) {
                return false;
            }

            var self = this;
            var recipient_done = $.Deferred();
            if (this.options.isLog) {
                recipient_done.resolve([]);
            } else {
                var checkedSuggestedPartners = this._getCheckedSuggestedPartners();
                recipient_done = this._checkSuggestedPartners(checkedSuggestedPartners);
            }
            recipient_done.then(function (partner_ids) {
                var context = {
                    default_parent_id: self.id,
                    default_body: utils.getTextToHTML(self.$input.val()),
                    default_attachment_ids: _.pluck(self.get('attachment_ids'), 'id'),
                    default_partner_ids: partner_ids,
                    default_is_internal: self.options.isInternal,
                    default_is_log: self.options.isLog,
                    mail_post_autofollow: true,
                };

                if (self.context.default_model && self.context.default_res_id) {
                    context.default_model = self.context.default_model;
                    context.default_res_id = self.context.default_res_id;
                }

                var action = {
                    type: 'ir.actions.act_window',
                    res_model: 'mail.compose.message',
                    view_mode: 'form',
                    view_type: 'form',
                    views: [
                        [false, 'form']
                    ],
                    target: 'new',
                    context: context,
                };
                self.do_action(action, {
                    on_close: self.trigger.bind(self, 'need_refresh'),
                }).then(self.trigger.bind(self, 'close_composer'));
            });
        }

    });

    return ChatterComposerInternal;

});

odoo.define('mail_internal.Chatter', function (require) {
    "use strict";
    require('web.dom_ready');
    var Chatter = require('mail.Chatter');

    Chatter.include({
        events: _.extend({}, Chatter.prototype.events, {
            'click .o_chatter_button_new_internal_message': '_onOpenComposerInternalMessage',
        }),
        start: function () {
            return this._super.apply(this, arguments);
        },
        // handlers
        _onOpenComposerInternalMessage: function () {
            this._openComposer({ isLog: true, isInternal: true });
        },
        // private
        _closeComposer: function (force) {
            this._super.apply(this, arguments);
            if (this._composer && (this._composer.isEmpty() || force)) {
                this.$el.removeClass('o_chatter_composer_active');
                this.$('.o_chatter_button_new_internal_message').removeClass('o_active');
                this._composer.do_hide();
                this._composer.clearComposer();
            }
        },
        _openComposer: function (options) {
            var self = this;
            this._super.apply(this, arguments);
            this._composer.options.isInternal = options && options.isInternal || false;
            this._composer.insertAfter(this.$('.o_chatter_topbar')).then(function () {
                self.$('.o_chatter_button_new_internal_message').removeClass('o_active');
                self.$('.o_chatter_button_new_internal_message').toggleClass('o_active', self._composer.options.isInternal && self._composer.options.isLog);
                // Show send message when neither log or internal
                self.$('.o_chatter_button_log_note').toggleClass('o_active', self._composer.options.isLog && !self._composer.options.isInternal);
                self.$('.o_chatter_button_new_message').toggleClass('o_active', !self._composer.options.isLog && !self._composer.options.isInternal);
            });
        },
    });

});
