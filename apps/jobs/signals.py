import django.dispatch
from django.dispatch import receiver


# Custom signal for EstWorksheet status updates - only fired when needed
estimate_status_changed_for_worksheet = django.dispatch.Signal()


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