odoo.define('spreadsheet_ux.helpers', function (require) {
    'use strict';

    const helpers = require('@spreadsheet/global_filters/helpers');
    const { Domain } = require('@web/core/domain');
    const { serializeDate } = require('@web/core/l10n/dates');

    const { checkFiltersTypeValueCombination, getRelativeDateDomain } = helpers;

    helpers.checkFiltersTypeValueCombination = function(type, value) {
        return value === 'today' ? 0 : checkFiltersTypeValueCombination.apply(this, arguments);
    };

    helpers.getRelativeDateDomain = function(now, offset, rangeType, fieldName, fieldType) {
        if (rangeType === 'today') {
            const startDate = now.startOf('day');
            const endDate = now.endOf('day');
            return new Domain(["&", [fieldName, ">=", serializeDate(startDate)], [fieldName, "<=", serializeDate(endDate)]]);
        }
        return getRelativeDateDomain.apply(this, arguments);
    };

    return helpers;
});
