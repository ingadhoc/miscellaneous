odoo.define('report_pdf_preview.report', function (require) {
    'use strict';

    var ActionManager = require('web.ActionManager');
    var core = require('web.core');
    var crash_manager = require('web.crash_manager');
    var framework = require('web.framework');

    var PreviewDialog = require('report_pdf_preview.PreviewDialog');
    var PreviewGenerator = require('report_pdf_preview.PreviewGenerator');

    var _t = core._t;
    var _lt = core._lt;

    var wkhtmltopdf_state;

    ActionManager.include({
        _executeReportAction: function (action, options) {
            var self = this;
            action = _.clone(action);
            var _super = _.bind(this._super, this);

            if (action.report_type === 'qweb-pdf') {
                return this.call('report', 'checkWkhtmltopdf').then(function (state) {
                    var active_ids_path = '/' + action.context.active_ids.join(',');
                    var url = '/report/pdf/' + action.report_name + active_ids_path;
                    var filename = action.report_name;
                    var title = action.display_name;
                    var def = $.Deferred()
                    var dialog = PreviewDialog.createPreviewDialog(self, url, false, "pdf", title);
                    $.when(dialog, dialog._opened).then(function (dialog) {
                        var a = 1;
                        dialog.$modal.find('.preview-download').hide();

                    })
                    framework.unblockUI();
                });
            } else if (action.report_type === 'aeroo') {
                return this._rpc({route: '/report/check_aeroo_pdf/' + action.report_name}).then(function(result){
                    if (result === true){
                        var active_ids_path = '/' + action.context.active_ids.join(',');
                        var url = '/report/aeroo/' + action.report_name + active_ids_path;
                        var filename = action.report_name;
                        var title = action.display_name;
                        var def = $.Deferred()
                        var dialog=PreviewDialog.createPreviewDialog(self, url, false, "pdf", title);
                        $.when(dialog,dialog._opened).then(function (dialog) {
                            var a=1;
                            dialog.$modal.find('.preview-download').hide();
                        })
                        framework.unblockUI();
                    } else {
                        return _super(action, options);
                    }
                });
            } else {
                return self._super(action, options);
            }

        }
    });

});
