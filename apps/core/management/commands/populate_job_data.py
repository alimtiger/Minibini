from .populate_data import Command as BaseCommand


class Command(BaseCommand):
    """Command to populate job-specific test data."""

    fixture_dir = 'job_data'
    help = 'Drop and recreate database with job test data for development'
