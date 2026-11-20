.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==================
Google Calendar UX
==================

Reconnecting Google Calendar from the Calendar "Google" button no longer hangs.

* Without a Google token, the button goes straight to Google's consent screen.
  Odoo standard first marks every event of the user (one year back and one
  year ahead) to be resent. The events organized by a connected colleague are
  sent right away, one by one, with the colleague's account, and may notify
  their attendees; with many events the browser times out before reaching
  Google, and a second click ends in a ``SerializationFailure``. The marks are
  not needed: nothing can be sent without a token, and events edited while
  disconnected are already marked.
* With a token (synchronization only stopped), the button behaves as standard.
* The button ignores a second click while the first one is running.

Installation
============

The module installs automatically wherever ``google_calendar`` is installed.

On install, every user without a Google token gets the same result as
"Reset Account" with "Leave them untouched" and "Synchronize only new events":
the events they organize that are already in Google stop being marked for
resend, and their sync token is cleared, so the next connection starts with a
full synchronization that does not notify attendees. Changes made in Odoo while
the user was disconnected are not sent to Google. Users with a Google token are
not touched: neither their credentials nor their events.

Configuration
=============

Nothing to configure.

Usage
=====

Go to Calendar and press "Google".

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/miscellaneous/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* |company| |icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
