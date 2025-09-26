from .populate_data import Command as BaseCommand


class Command(BaseCommand):
    """Command to populate contact-specific test data."""

    fixture_dir = 'contact_data'
    help = 'Drop and recreate database with contact test data for development'