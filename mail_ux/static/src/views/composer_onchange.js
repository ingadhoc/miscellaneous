import { ORM } from "@web/core/orm_service";
import { patch } from "@web/core/utils/patch";

// The composer dialog is rebuilt when an overlay (e.g. a tooltip) changes while it loads,
// which sends the same initial onchange again: reuse the pending one.
const pendingComposerOnchanges = new Map();

patch(ORM.prototype, {
    call(model, method, args = [], kwargs = {}) {
        const isInitialComposerOnchange =
            model === "mail.compose.message" &&
            method === "onchange" &&
            Array.isArray(args[2]) &&
            !args[2].length;
        if (!isInitialComposerOnchange) {
            return super.call(...arguments);
        }
        const key = JSON.stringify([args, kwargs]);
        let prom = pendingComposerOnchanges.get(key);
        if (!prom) {
            prom = super.call(...arguments);
            pendingComposerOnchanges.set(key, prom);
            prom.finally(() => pendingComposerOnchanges.delete(key)).catch(() => {});
        }
        return prom.then((result) => structuredClone(result));
    },
});
