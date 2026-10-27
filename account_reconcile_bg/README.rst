Account Reconcile Background
============================

This module enables background processing for bank reconciliation operations when dealing with large payment batches, preventing timeouts and improving user experience.

**Table of contents**

.. contents::
   :local:

Overview
========

When reconciling a bank statement line with a large batch payment (many payments included in a single batch), the operation can take a long time and may cause timeouts. This module solves this problem by automatically processing large reconciliations in the background, allowing users to continue working while the reconciliation completes.

Features
========

* **Automatic Background Processing**: Large reconciliations are automatically sent to background processing
* **Configurable Threshold**: System parameter to control when background processing kicks in (default: 100 payments)
* **User Notifications**: Users receive a notification when the reconciliation is enqueued, and the background job reports the result with a link to the statement line
* **Locked Statement Line**: While the reconciliation runs in background, the statement line cannot be reconciled again and its amount and currency cannot be modified
* **No UI Blocking**: Users can continue reconciling other transactions while large batches process
* **Seamless Integration**: Works transparently with existing bank reconciliation workflow

How It Works
============

The module monitors the number of payments of the batch payment being reconciled with a bank statement line:

1. When a batch payment is set on a bank statement line, it counts the payments of the batch
2. If the count is **below the threshold** (default 100), the reconciliation proceeds normally (synchronous)
3. If the count is **equal to or above the threshold**, the statement line is flagged and the reconciliation is enqueued as a background job
4. The user receives an immediate notification and can continue working
5. When the background job completes or fails, the flag is cleared and the job reports the result (success or error) with a link to the statement line. The flag is also cleared if the job is cancelled

Configuration
=============

The threshold for background processing can be configured via system parameters:

* Navigate to **Settings > Technical > Parameters > System Parameters**
* Find or create the parameter ``account_reconcile_bg.lines_threshold``
* Default value: ``100``
* Set to a higher value to process larger reconciliations synchronously
* Set to a lower value to send more reconciliations to background

Technical Details
=================

Dependencies
------------

* ``account_batch_payment``: Odoo Enterprise batch payments, reconciled with bank statement lines
* ``base_bg``: Background job processing system

Model Inheritance
-----------------

``account.bank.statement.line``:

* ``reconciliation_in_background``: Flag set while the line is being reconciled in background
* ``set_batch_payment_bank_statement_line()``: Detects large batch payments and routes them to background
* ``_enqueue_batch_reconciliation()``: Flags the line and enqueues the job using base_bg
* ``_bg_set_batch_payment_bank_statement_line()``: Executes the actual reconciliation in background
* ``_check_reconciliation_in_background()``: Prevents modifying the amount or currency of a flagged line

``account.move.line``:

* ``reconciliation_in_background``: Flag field

``bg.job``:

* ``cancel()`` and ``fail()``: Clear the flag of the statement line when a reconciliation job is cancelled or fails

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
