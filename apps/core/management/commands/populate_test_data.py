from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.contacts.models import Contact
from apps.jobs.models import Job

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate the database with test data for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before adding test data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Job.objects.all().delete()
            Contact.objects.all().delete()
            User.objects.filter(username='dev_user').delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        # Create default development user
        self.stdout.write('Creating default development user...')
        default_user, created = User.objects.get_or_create(
            username='dev_user',
            defaults={
                'email': 'dev@example.com',
                'first_name': 'Dev',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            default_user.set_password('dev_password')
            default_user.save()
            self.stdout.write(self.style.SUCCESS('Default user created.'))
        else:
            self.stdout.write('Default user already exists.')

        self.stdout.write('Loading webserver test data from fixtures...')
        try:
            call_command('loaddata', 'webserver_test_data.json', verbosity=0)
            self.stdout.write(self.style.SUCCESS('Test data populated successfully!'))
            
            # Show summary of what was loaded
            contact_count = Contact.objects.count()
            job_count = Job.objects.count()
            self.stdout.write(f'Loaded {contact_count} contacts and {job_count} jobs.')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading test data: {e}'))