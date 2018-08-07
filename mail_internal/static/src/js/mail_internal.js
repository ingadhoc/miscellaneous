odoo.define('mail_internal.ChatterComposer', function (require) {
    "use strict";

    var ChatterComposer = require('mail.ChatterComposer');
    var ChatterComposerInternal = ChatterComposer.include({

        preprocess_message: function () {
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
                if (self.options.is_log) {
                    message.subtype = 'mail.mt_note';
                }
                if (self.options.is_internal) {
                    message.subtype = 'mail_internal.mt_internal_message';
                }

                // Partner_ids
                if (!self.options.is_log && !self.options.is_internal) {

                    var checked_suggested_partners = self.get_checked_suggested_partners();
                    self.check_suggested_partners(checked_suggested_partners).done(function (partner_ids) {
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
            this._openComposer({
                is_internal: true,
                is_log: false
            });
        },
        // private
        _closeComposer: function (force) {
            this._super.apply(this, arguments);
            if (this.composer && (this.composer.is_empty() || force)) {
                this.$el.removeClass('o_chatter_composer_active');
                this.$('.o_chatter_button_new_internal_message').removeClass('o_active');
                this.composer.do_hide();
                this.composer.clear_composer();
            }
        },
        _openComposer: function (options) {
            var self = this;
            this._super.apply(this, arguments);
            this.composer.options.is_internal = options && options.is_internal || false;
            this.composer.insertAfter(this.$('.o_chatter_topbar')).then(function () {
                self.$('.o_chatter_button_new_internal_message').removeClass('o_active');
                self.$('.o_chatter_button_new_internal_message').toggleClass('o_active', self.composer.options.is_internal);
                // Show send message when neither log or internal
                self.$('.o_chatter_button_new_message').toggleClass('o_active', !self.composer.options.is_log && !self.composer.options.is_internal);
            });
        },
    });

});
