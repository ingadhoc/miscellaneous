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

 * Send chatter messages and notes with a delay set by each user: the message is scheduled and can be edited, sent now or cancelled before it goes out.
 * A user who can post on a record can schedule a message on it, even with read-only access to the record.
 * The author of a scheduled message can cancel it, besides administrators and users who can edit the record.
 * Scheduled messages keep the recipients, the CC and the subject loaded in the chatter.
 * Send a test email from an outgoing mail server, also in neutralized databases.


Installation
============

Only install the module.

Configuration
=============

Each user will be allowed to set it own "delay time" for sending messages and/or notes. To set it up just go to "My preferences" by clicking in the avatar in the top-right corner, then in the field "Send message delay" just fill it up with the delay time expected (in seconds), and Save it.

Usage
=====

* With a delay set, a message posted from the chatter shows up as a scheduled message. Before the delay ends, its author can edit it, send it now or cancel it.
* Emails sent in mass mail mode are not scheduled in the chatter: the delay goes to the outgoing emails.
* To send a test email, go to Settings > Technical > Email > Outgoing Mail Servers (developer mode), open a server and click "Enviar mail de prueba". The connection is tested first; then fill in the recipient and click "Enviar prueba".

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
