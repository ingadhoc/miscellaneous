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
        const dataProxy = new Proxy(record.data, {
            get: (data, key) =>
                key === "view_group_hierarchy"
                    ? data.portal_advanced_view_group_hierarchy
                    : data[key],
        });
        const recordProxy = new Proxy(record, {
            get: (target, key) => {
                if (key === "data") {
                    return dataProxy;
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
