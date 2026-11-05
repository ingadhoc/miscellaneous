/** @odoo-module **/

import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/strings";
import { importRecordsItem } from "@base_import/import_records/import_records";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * Core hides the "Import records" gear menu item on small screens, and some
 * clients still want it there. Re-register the same item with core's condition
 * minus that check. The check cannot be delegated: core reads `isSmall` from
 * the `ui` service, not from the env it gets, so the condition is repeated
 * here and has to stay in sync with
 * base_import/static/src/import_records/import_records.js.
 */
cogMenuRegistry.add(
    "import-menu",
    {
        ...importRecordsItem,
        isDisplayed: ({ config }) =>
            config.actionType === "ir.actions.act_window" &&
            ["kanban", "list", "grid"].includes(config.viewType) &&
            exprToBoolean(config.viewArch.getAttribute("import"), true) &&
            exprToBoolean(config.viewArch.getAttribute("create"), true),
    },
    { force: true, sequence: 1 }
);
