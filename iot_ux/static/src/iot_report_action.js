import {
    IOT_REPORT_PREFERENCE_LOCAL_STORAGE_KEY,
    setReportIdInBrowserLocalStorage,
} from "@iot/client_action/delete_local_storage";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

import { getSelectedPrintersForReport, printReport } from "@iot/iot_report_action";


export async function getSelectedPrintersForReportUx(reportId, env) {
    const { orm, action, ui } = env.services;
    const deviceSettingsByReportId = JSON.parse(browser.localStorage.getItem(IOT_REPORT_PREFERENCE_LOCAL_STORAGE_KEY));
    const deviceSettings = deviceSettingsByReportId?.[reportId];
    if (!deviceSettings ) {
        const rule= await orm.call(
            "ir.actions.report.iot.rule",
            "search_read",
            [[['report_id', '=', reportId], ['user_id', '=', user.userId], ['device_id', '!=', false]],
            ["skip_dialog", "device_id"]]);
        if (rule.length > 0) {
            const newDeviceSettings = {
                selectedDevices: [rule[0].device_id[0]],
                skipDialog: rule[0].skip_dialog,
            };
        setReportIdInBrowserLocalStorage(reportId, newDeviceSettings);
        }
    }
    return await getSelectedPrintersForReport(reportId, env);
}

async function iotReportActionHandler(action, options, env) {
    if (action.device_ids && action.device_ids.length) {
        action.data ??= {};
        const args = [action.id, action.context.active_ids, action.data];
        const reportId = action.id;
        const printerIds = await getSelectedPrintersForReportUx(reportId, env);

        if (!printerIds) {
            // If the user does not select any printer, fall back to normal printing
            return false;
        }

        env.services.ui.block();
        // Try longpolling then websocket
        await printReport(env, args, printerIds);
        env.services.ui.unblock();

        options.onClose?.();
        return true;
    }
}

registry
    .category("ir.actions.report handlers")
    .add("iot_report_action_handler", iotReportActionHandler, {force: true});
