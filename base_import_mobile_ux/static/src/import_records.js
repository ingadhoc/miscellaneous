/** @odoo-module **/

import { registry } from "@web/core/registry";
import { importRecordsItem } from "@base_import/import_records/import_records";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * Core hides the "Import records" gear menu item on small screens
 * (isDisplayed checks `!isSmall`, see base_import/import_records.js).
 * That's intentional for the default import wizard, but some clients
 * still want the entry available on mobile. Re-register the same item,
 * only forcing `isSmall` to false so the rest of the original condition
 * (view type, `import`/`create` arch attributes, action type) still applies.
 *
 * Owl envs are built with `Object.create` (prototypal, frozen) — `config`
 * lives on a prototype, not as an own property. A plain `{...env}` spread
 * only copies own properties and drops `config`, so `Object.create` is used
 * here to shadow `isSmall` while keeping the rest of the chain intact.
 */
cogMenuRegistry.add(
    "import-menu",
    {
        ...importRecordsItem,
        isDisplayed: (env) =>
            importRecordsItem.isDisplayed(
                Object.create(env, { isSmall: { value: false, enumerable: true } })
            ),
    },
    { force: true, sequence: 1 }
);
