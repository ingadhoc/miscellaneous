import logging

from odoo.tools import SQL

_logger = logging.getLogger(__name__)

DISCONNECTED_USERS = SQL(
    """
    SELECT u.id
      FROM res_users u
      LEFT JOIN res_users_settings s ON s.user_id = u.id
     WHERE COALESCE(s.google_calendar_rtoken, '') = ''
    """
)


def post_init_hook(env):
    """Same as "Reset Account" with "Leave them untouched" and "Synchronize only new
    events" for every user without a Google token, so reconnecting does not resend
    (and notify) what the restart button left marked."""
    env.flush_all()
    cr = env.cr
    cr.execute(
        SQL(
            """
            UPDATE calendar_event e
               SET need_sync = FALSE
             WHERE e.need_sync
               AND e.google_id IS NOT NULL
               AND e.user_id IN (%s)
            """,
            DISCONNECTED_USERS,
        )
    )
    events = cr.rowcount
    cr.execute(
        SQL(
            """
            UPDATE calendar_recurrence r
               SET need_sync = FALSE
              FROM calendar_event e
             WHERE r.base_event_id = e.id
               AND r.need_sync
               AND r.google_id IS NOT NULL
               AND e.user_id IN (%s)
            """,
            DISCONNECTED_USERS,
        )
    )
    recurrences = cr.rowcount
    cr.execute(
        SQL(
            """
            UPDATE res_users_settings
               SET google_calendar_sync_token = NULL,
                   google_calendar_cal_id = NULL
             WHERE COALESCE(google_calendar_rtoken, '') = ''
               AND (google_calendar_sync_token IS NOT NULL OR google_calendar_cal_id IS NOT NULL)
            """
        )
    )
    settings = cr.rowcount
    env.invalidate_all()
    _logger.info(
        "google_calendar_ux: need_sync cleared on %s events and %s recurrences, sync token cleared for %s users",
        events,
        recurrences,
        settings,
    )
