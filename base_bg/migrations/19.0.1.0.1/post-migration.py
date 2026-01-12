##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging
import uuid

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration script to set batch_id for existing jobs.

    Each existing job will be treated as a single-job batch:
    - batch_id: unique UUID for each job
    """
    cr.execute("""
        SELECT id FROM bg_job
        WHERE batch_id IS NULL
    """)
    job_ids = [row[0] for row in cr.fetchall()]
    for job_id in job_ids:
        batch_id = str(uuid.uuid4())
        cr.execute(
            """
            UPDATE bg_job
            SET batch_id = %s
            WHERE id = %s
        """,
            (batch_id, job_id),
        )
