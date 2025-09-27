import django.dispatch
from django.dispatch import receiver


# Custom signal for EstWorksheet status updates - only fired when needed
estimate_status_changed_for_worksheet = django.dispatch.Signal()

# Custom signal for Job status updates based on Estimate changes
estimate_status_changed_for_job = django.dispatch.Signal()


@receiver(estimate_status_changed_for_worksheet)
def update_estworksheet_status(sender, estimate, new_worksheet_status, **kwargs):
    """
    Update EstWorksheet status based on Estimate status change.
    This is only called when a relevant status change occurs.
    """
    from apps.jobs.models import EstWorksheet

    # Single efficient UPDATE query - affects 0 rows if no worksheets exist
    updated_count = EstWorksheet.objects.filter(
        estimate=estimate
    ).exclude(
        status=new_worksheet_status  # Don't update if already correct status
    ).update(
        status=new_worksheet_status
    )

    # Return count for testing/logging purposes
    return updated_count


@receiver(estimate_status_changed_for_job)
def update_job_status(sender, estimate, new_job_status, **kwargs):
    """
    Update Job status based on Estimate status change.

    Business rules:
    - When estimate is accepted, job becomes approved (unless already complete)
    - When approved estimate is superseded, job becomes blocked (unless already complete)
    """
    from apps.jobs.models import Job

    job = estimate.job

    # Don't update completed jobs
    if job.status == 'complete':
        return 0

    # Update job status if needed
    if job.status != new_job_status:
        job.status = new_job_status
        job.save()
        return 1

    return 0