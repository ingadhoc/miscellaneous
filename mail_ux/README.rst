.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=======
Mail UX
=======

 * Always send email with delay
 * Do not render the report of a mail template more than once while the mail composer is open. ``attachment_ids`` is a stored compute, so the web client recomputes it on every round trip and each recompute used to render the same PDF again (2 to 6 times per composer opening, leaving the orphan attachments behind). The already generated attachment is reused while the report, the record and the record's write_date are the same. The reuse window in seconds is set through the system parameter mail_ux.report_attachment_cache_ttl (default to 600; 0 disables the reuse).


Installation
============

Only install the module.

Configuration
=============

Each user will be allowed to set it own "delay time" for sending messages and/or notes. To set it up just go to "My preferences" by clicking in the avatar in the top-right corner, then in the field "Send message delay" just fill it up with the delay time expected (in seconds), and Save it.

Usage
=====

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
