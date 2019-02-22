console.log("cargo archivo");
odoo.define('mail_activity_board_ux.systray', function (require) {
    "use strict";

    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var session = require('web.session');
    var core = require('web.core');

    var ActivityMenu = Widget.extend({
        _onActivityFilterClick: function (event) {
            var data = _.extend({}, $(event.currentTarget).data(), $(event.target).data());
            if (data.res_model = 'crm.lead'){

            }
            var context = {};
            if (data.filter === 'my') {
                context['search_default_activities_overdue'] = 1;
                context['search_default_activities_today'] = 1;
            } else {
                context['search_default_activities_' + data.filter] = 1;
            }
            this.do_action({
                type: 'ir.actions.act_window',
                name: data.model_name,
                res_model:  data.res_model,
                views: [[false, 'kanban'], [false, 'form']],
                search_view_id: [false],
                domain: [['activity_user_id', '=', session.uid]],
                context:context,
            });
        },
    });

    SystrayMenu.Items.push(ActivityMenu);
    return {
        ActivityMenu: ActivityMenu,
};
});