Account Reconcile Background
============================

This module enables background processing for bank reconciliation operations when dealing with large payment batches, preventing timeouts and improving user experience.

**Table of contents**

.. contents::
   :local:

Overview
========

When reconciling large payment batches (e.g., multiple payments included in a single batch) with a bank statement line, the operation can take a long time and may cause timeouts. This module solves this problem by automatically processing large reconciliations in the background, allowing users to continue working while the reconciliation completes.

Features
========

* **Automatic Background Processing**: Large reconciliations are automatically sent to background processing
* **Configurable Threshold**: System parameter to control when background processing kicks in (default: 50 lines)
* **User Notifications**: Users receive notifications when background reconciliation completes
* **No UI Blocking**: Users can continue reconciling other transactions while large batches process
* **Seamless Integration**: Works transparently with existing bank reconciliation workflow

How It Works
============

The module monitors the number of lines being reconciled in the bank reconciliation widget:

1. When validating a reconciliation, it counts the number of source lines
2. If the count is **below the threshold** (default 50), the reconciliation proceeds normally (synchronous)
3. If the count is **above the threshold**, the reconciliation is enqueued as a background job
4. The user receives an immediate success notification and can continue working
5. When the background job completes, the user is notified via internal message

Configuration
=============

The threshold for background processing can be configured via system parameters:

* Navigate to **Settings > Technical > Parameters > System Parameters**
* Find or create the parameter ``account_reconcile_bg.lines_threshold``
* Default value: ``50``
* Set to a higher value to process larger reconciliations synchronously
* Set to a lower value to send more reconciliations to background

Technical Details
=================

Dependencies
------------

* ``account_accountant``: Odoo Enterprise accounting module with bank reconciliation
* ``base_bg``: Background job processing system

Model Inheritance
-----------------

The module inherits from ``bank.rec.widget`` and overrides:

* ``_js_action_validate()``: Detects large reconciliations and routes to background
* ``_validate_in_background()``: Enqueues the job using base_bg
* ``_do_validate()``: Executes the actual validation in background

Credits
=======

Authors
-------

* ADHOC SA

Contributors
------------

* ADHOC SA

Maintainers
-----------

This module is maintained by ADHOC SA.
