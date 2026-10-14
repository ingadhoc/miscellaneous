import { registry } from "@web/core/registry";
// The native widget only registers itself: import it so it is loaded before we read it from the registry.
import "@web/webclient/res_user_group_ids_field/res_user_group_ids_field";

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
        // In Owl 3 the props are live getters, updated in place (e.g. when the pager moves to another
        // user): wrap them instead of copying them, so `record` is always the current one.
        const props = this.props;
        this.props = new Proxy(props, {
            get: (target, key) => (key === "record" ? wrapRecord(target.record) : target[key]),
        });
        super.setup();
    }
}

function wrapRecord(record) {
    return new Proxy(record, {
        get: (target, key) => {
            if (key === "data") {
                // Wrap `target.data` fresh on every access instead of caching a single Proxy
                // bound to the `record.data` reference seen at setup() time: on a cold load,
                // the record can still be hydrating when setup() runs, and Odoo later swaps in
                // the fully-loaded `data` object rather than mutating the placeholder in place.
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
}

fieldsRegistry.add("portal_advanced_group_ids", {
    ...nativeDef,
    component: PortalAdvancedGroupIdsField,
    fieldDependencies: [
        ...(nativeDef.fieldDependencies || []),
        { name: "portal_advanced_view_group_hierarchy", type: "json", readonly: true },
    ],
});
