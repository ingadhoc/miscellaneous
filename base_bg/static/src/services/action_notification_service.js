/** @odoo-module **/

import { registry } from "@web/core/registry";


export const actionNotificationService = {
    dependencies: ["bus_service", "notification", "action"],

    start(env, { bus_service, notification, action }) {
        bus_service.subscribe("action_notification", ({ message, type, action_button}) => {
            if (!action_button) {
                notification.add(message, { type });
                return;
            } else {
                const buttons = [{
                    name: action_button.name,
                    primary: false,
                    onClick: () => {
                        action.doAction(action_button);
                    },
                }];
                notification.add(message, { type, buttons });
            }
        });
    }
};

registry.category("services").add("actionNotification", actionNotificationService);
