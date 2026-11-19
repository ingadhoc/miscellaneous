import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("printer.type.handlers").add("printnode", async (printer, _duplex, jobs, services) => {
    const { orm, notification } = services;
    for (const job of jobs.filter((job) => job.type === "printnode")) {
        await orm.call("printer.printer", "printnode_print", [printer.id, job]);
        notification.add(_t("Print job successfully sent to %s via PrintNode", printer.name), {
            type: "success",
        });
    }
});
