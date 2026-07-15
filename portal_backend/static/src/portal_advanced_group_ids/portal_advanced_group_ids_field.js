import { registry } from "@web/core/registry";

/**
 * Same widget as the native `res_user_group_ids` (privilege-based selection dropdowns), but
 * restricted to the "Advanced Portal" category, so a Portal Backend user can be granted those
 * backend accesses with the standard look & feel.
 *
 * Implementation: reuse the native component verbatim and only redirect where it reads the group
 * hierarchy to our pre-filtered `portal_advanced_view_group_hierarchy` field (built server-side,
 * containing only the Advanced Portal category). The widget is bound to `portal_advanced_group_ids`,
 * whose inverse merges the selection back into `group_ids` without touching the user-type groups.
 */
const fieldsRegistry = registry.category("fields");
const nativeDef = fieldsRegistry.get("res_user_group_ids");

class PortalAdvancedGroupIdsField extends nativeDef.component {
    setup() {
        const record = this.props.record;
        const recordProxy = new Proxy(record, {
            get: (target, key) => {
                if (key === "data") {
                    // Wrap `target.data` fresh on every access instead of caching a single Proxy
                    // bound to the `record.data` reference seen at setup() time: on a cold load,
                    // the record can still be hydrating when setup() runs, and Odoo later swaps in
                    // the fully-loaded `data` object rather than mutating the placeholder in place.
                    // A one-time-captured proxy keeps pointing at that stale placeholder forever,
                    // so the widget renders the group selected before the real data arrived (fixed
                    // only by a second reload, once the swap already happened on the previous load).
                    return new Proxy(target.data, {
                        get: (data, dataKey) =>
                            dataKey === "view_group_hierarchy"
                                ? data.portal_advanced_view_group_hierarchy
                                : data[dataKey],
                    });
                }
                const value = target[key];
                return typeof value === "function" ? value.bind(target) : value;
            },
        });
        this.props = { ...this.props, record: recordProxy };
        super.setup();
    }
}

fieldsRegistry.add("portal_advanced_group_ids", {
    ...nativeDef,
    component: PortalAdvancedGroupIdsField,
    fieldDependencies: [
        ...(nativeDef.fieldDependencies || []),
        { name: "portal_advanced_view_group_hierarchy", type: "json", readonly: true },
    ],
});
