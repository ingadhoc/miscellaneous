odoo.define('mail.Discuss.extenction', function (require) {
    "use strict";
var Discuss = require('mail.Discuss');

var core = require('web.core');
var _t = core._t

Discuss.include({
    init: function (parent, action, options) {
        this._super.apply(this, arguments);},
    /**
     * @override
     */

    _onMarkAllAsReadClicked: function () {
        if (confirm("Esta a punto de eliminar los mensajes de la bandeja ¿Desea continuar?"))
        {
            this._thread.markAllMessagesAsRead(this.domain);
        }
    },

})
})
