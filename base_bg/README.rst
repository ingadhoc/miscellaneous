Base Background Jobs
====================

This module provides a background job processing system for Odoo that allows executing long-running operations asynchronously without blocking the user interface.

**Table of contents**

.. contents::
   :local:

Overview
========

The Base Background Jobs module introduces a powerful system for handling time-consuming operations asynchronously. Instead of making users wait for long-running processes like data imports, exports, or complex calculations, these operations can be queued and executed in the background while users continue working.

The module provides a **mixin class** ``base.bg`` that can be inherited by any model to gain background job capabilities through the ``bg_enqueue()`` method.

Features
========

* **Easy Integration**: Simple mixin inheritance to add background job capabilities to any model
* **Asynchronous Job Execution**: Execute long-running operations without blocking the UI
* **Automatic Job Queuing**: Jobs are queued and processed automatically by scheduled actions
* **Intelligent Retry Mechanism**: Failed jobs are automatically retried with configurable limits
* **Real-time Job Monitoring**: Complete visibility of job status, execution time, and error details
* **Smart User Notifications**: Users receive notifications via internal messages when jobs complete
* **Multi-worker Support**: Supports multiple cron workers for parallel job processing
* **Context Preservation**: Jobs maintain original user context, permissions, and record state
* **Automatic Cron Triggering**: Cron jobs are triggered immediately when new jobs are enqueued

Job States
-----------

* **Enqueued**: Job is waiting to be processed
* **Running**: Job is currently being executed
* **Done**: Job completed successfully
* **Failed**: Job failed after all retry attempts
* **Canceled**: Job was manually canceled

Usage
=====

Basic Setup
-----------

To add background job capabilities to your model, inherit from the ``base.bg`` mixin:

.. code-block:: python

    from odoo import models, fields, api

    class MyModel(models.Model):
        _name = 'my.model'
        _inherit = ['base.bg']  # Add the mixin
        _description = 'My Model with Background Jobs'

        name = fields.Char('Name')

        def my_long_process(self, param1, param2=None):
            """A method that takes time to execute"""
            # Your time-consuming logic here
            for i in range(1000):
                # Simulate heavy processing
                pass
            return f"Processed {param1} successfully"

        def action_start_background_process(self):
            """Button action to start background processing"""
            return self.bg_enqueue('my_long_process', 'test_param', param2='value')

Using bg_enqueue()
------------------

The ``bg_enqueue()`` method is the primary way to create background jobs:

.. code-block:: python

    # Basic usage - enqueue a method call
    result = record.bg_enqueue('method_name')

    # With arguments
    result = record.bg_enqueue('method_name', arg1, arg2, kwarg1='value')

    # With custom job name and retry configuration
    result = record.bg_enqueue(
        'method_name',
        arg1,
        arg2,
        name='Custom Job Name',
        max_retries=5
    )

The method returns a notification action that informs the user the job has been queued.

Real-world Examples
===================

Example 1: Background Data Export
----------------------------------

.. code-block:: python

    class SaleOrder(models.Model):
        _inherit = ['sale.order', 'base.bg']

        def action_export_to_csv_background(self):
            """Export selected orders to CSV in background"""
            return self.bg_enqueue(
                '_export_orders_to_csv',
                name=f'Export {len(self)} Sale Orders',
                max_retries=2
            )

        def _export_orders_to_csv(self):
            """Private method that performs the actual export"""
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(['Order', 'Customer', 'Total', 'Date'])

            # Write data
            for order in self:
                writer.writerow([
                    order.name,
                    order.partner_id.name,
                    order.amount_total,
                    order.date_order.strftime('%Y-%m-%d')
                ])

            # Save file or send email with attachment
            # ...

            return f"Successfully exported {len(self)} orders to CSV"


Advanced Usage
==============

Custom Context and Arguments
-----------------------------

The ``bg_enqueue()`` method automatically handles:

* **Record Context**: Current user, company, language settings
* **Record IDs**: The recordset is reconstructed in the background job
* **Arguments**: All positional and keyword arguments are serialized

.. code-block:: python

    # The method will receive the same recordset and arguments
    records.with_context(special_mode=True).bg_enqueue(
        'process_records',
        'param1',
        special_option=True
    )

Error Handling in Background Methods
------------------------------------

.. code-block:: python

    def _background_process_with_error_handling(self):
        """Background method with proper error handling"""
        try:
            # Your processing logic
            result = self._do_complex_processing()

            # Log success
            _logger.info(f"Successfully processed {len(self)} records")

            return f"Processing completed successfully: {result}"

        except Exception as e:
            # Log the error for debugging
            _logger.error(f"Error processing records: {str(e)}")

            # Re-raise to trigger retry mechanism
            raise

Monitoring and Management
=========================

Job Monitoring Interface
-------------------------

Users can monitor their background jobs through:

**Settings > Technical > Background Jobs > Jobs**

The interface provides:

* **List View**: Overview of all jobs with status indicators and execution times
* **Form View**: Detailed job information including arguments, context, and error messages
* **Smart Filters**: Filter by state, date, model, user, etc.
* **Bulk Actions**: Retry multiple failed jobs or cancel enqueued jobs
* **Search**: Find jobs by name, model, or method

Job Information Available
-------------------------

Each job record contains:

* **Execution Details**: Start time, end time, duration
* **Arguments**: Serialized method arguments and keyword arguments
* **Context**: User context, company, language settings
* **Error Information**: Full error messages and retry count
* **User Information**: Job creator and execution permissions

Manual Job Management
---------------------

From the job form view, users can:

* **Retry Failed Jobs**: Restart failed jobs manually
* **Cancel Enqueued Jobs**: Cancel jobs that haven't started yet
* **View Execution Details**: See complete job information and logs

Configuration
=============

Automatic Processing
--------------------

The module creates a scheduled action that:

* Runs every minute by default
* Processes up to 5 jobs per minute per worker
* Automatically triggered when new jobs are enqueued (no waiting)
* Supports multiple workers for parallel processing

Timeout Management
------------------

A separate scheduled action monitors running jobs:

* Detects jobs running longer than 5 hours (configurable)
* Automatically marks them as failed with timeout error
* Prevents stuck jobs from blocking the queue

Security and Permissions
========================

Job Execution Security
----------------------

* Jobs execute with the permissions of their creator
* Original user context is preserved (company, language, etc.)
* Record access rules are enforced during job execution
* Jobs cannot escalate permissions beyond the creator's rights

Data Security
-------------

* Job arguments are stored as JSON in the database
* Avoid passing sensitive data like passwords in arguments
* Consider encrypting sensitive data before passing to background jobs
* Job results may contain sensitive information in success messages

User Access Control
-------------------

* Regular users can create, read, and write their own jobs
* System administrators have full access including delete permissions
* Users can only see and manage their own background jobs
* Managers can see jobs from their team members (if configured)

Technical Details
=================

Architecture
------------

The module consists of:

* **base.bg Mixin**: Abstract model providing ``bg_enqueue()`` method
* **bg.job Model**: Stores job data, state, and execution information
* **Cron Jobs**: Automated job processing and monitoring
* **Notification System**: Integration with Odoo's messaging for user notifications

Performance Considerations
--------------------------

* Jobs are processed sequentially within each worker
* Large recordsets are handled efficiently through ID serialization
* JSON serialization may impact performance with very large arguments
* Database commits are handled automatically during job execution

Limitations
-----------

* No built-in progress reporting (must be implemented in job methods)
* Jobs cannot return complex objects (only strings/basic types for notifications)
* Large arguments/context may impact database performance
* Jobs are lost if the database is restored to a point before they were created


Troubleshooting
===============

Common Issues
-------------

**Jobs stay in 'enqueued' state**
  - Check if cron jobs are running
  - Verify the scheduled action is active
  - Check server logs for cron errors

**Jobs fail immediately**
  - Check method exists and is callable
  - Verify record permissions and access rules
  - Review error messages in job form view

**Performance problems**
  - Monitor job execution times
  - Check for large argument serialization
  - Consider splitting large jobs into smaller ones

Debug Mode
----------

To debug background jobs:

1. Enable developer mode
2. Check job details in the background jobs menu
3. Review server logs for detailed error information
4. Test methods directly before enqueueing them

Credits
=======

Authors
-------

* ADHOC SA

Contributors
------------

* ADHOC SA Development Team

Maintainers
-----------

This module is maintained by ADHOC SA.

.. image:: https://www.adhoc.com.ar/logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar
