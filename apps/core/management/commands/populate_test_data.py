import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import connection
from apps.contacts.models import Contact
from apps.jobs.models import Job

User = get_user_model()


class Command(BaseCommand):
    help = 'Drop and recreate database with test data for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-drop',
            action='store_true',
            help='Skip dropping the database (useful if database is already empty)',
        )

    def handle(self, *args, **options):
        db_name = settings.DATABASES['default']['NAME']
        db_user = settings.DATABASES['default']['USER']
        db_password = settings.DATABASES['default']['PASSWORD']
        db_host = settings.DATABASES['default']['HOST']
        db_port = settings.DATABASES['default']['PORT']

        if not options['skip_drop']:
            self.stdout.write('Clearing all data from database...')

            try:
                # Use Django's flush command to clear all data
                # This preserves the database structure but removes all data
                call_command('flush', '--no-input', verbosity=0)
                self.stdout.write(self.style.SUCCESS('Database cleared.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error clearing database: {e}'))
                return

        # Run migrations
        self.stdout.write('Running migrations...')
        try:
            call_command('migrate', '--no-input', verbosity=0)
            self.stdout.write(self.style.SUCCESS('Migrations completed.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error running migrations: {e}'))
            return

        # Create default development user
        self.stdout.write('Creating default development user...')
        try:
            default_user = User.objects.create_user(
                username='dev_user',
                email='dev@example.com',
                password='dev_password',
                first_name='Dev',
                last_name='User',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(self.style.SUCCESS('Default user created.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating default user: {e}'))
            return

        # Load all fixtures from test_data directory
        fixtures_dir = os.path.join('fixtures', 'test_data')
        if not os.path.exists(fixtures_dir):
            self.stdout.write(self.style.ERROR(f'Fixtures directory {fixtures_dir} does not exist.'))
            return

        # Get all JSON files in the directory, sorted alphabetically
        fixture_files = sorted([f for f in os.listdir(fixtures_dir) if f.endswith('.json')])

        if not fixture_files:
            self.stdout.write(self.style.WARNING('No fixture files found in test_data directory.'))
            return

        self.stdout.write(f'Loading {len(fixture_files)} fixture files...')

        for fixture_file in fixture_files:
            fixture_path = os.path.join('fixtures', 'test_data', fixture_file)
            self.stdout.write(f'  Loading {fixture_file}...')
            try:
                call_command('loaddata', fixture_path, verbosity=0)
                self.stdout.write(self.style.SUCCESS(f'    ✓ {fixture_file} loaded'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    ✗ Error loading {fixture_file}: {e}'))
                return

        # Show summary of what was loaded
        self.stdout.write('\n' + self.style.SUCCESS('Test data populated successfully!'))
        self.stdout.write('\nDatabase summary:')
        self.stdout.write(f'  Users: {User.objects.count()}')
        self.stdout.write(f'  Contacts: {Contact.objects.count()}')
        self.stdout.write(f'  Jobs: {Job.objects.count()}')