import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarController.prototype, {
    async onGoogleSyncCalendar() {
        // A second click while the first one runs ends in a SerializationFailure.
        if (this.googleSyncRunning) {
            return;
        }
        this.googleSyncRunning = true;
        try {
            return await super.onGoogleSyncCalendar(...arguments);
        } finally {
            this.googleSyncRunning = false;
        }
    },
});
