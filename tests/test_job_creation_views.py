from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.jobs.models import Job
from apps.contacts.models import Contact


class JobCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.contact1 = Contact.objects.create(name="Test Customer 1")
        self.contact2 = Contact.objects.create(name="Test Customer 2")
        self.url = reverse('jobs:create')

    def test_job_create_view_get(self):
        """Test GET request to job creation form"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'jobs/job_create.html')
        self.assertContains(response, 'Create New Job')
        self.assertContains(response, 'Select Contact')

    def test_job_create_view_get_with_preselected_contact(self):
        """Test GET request with pre-selected contact from query parameter"""
        response = self.client.get(f"{self.url}?contact_id={self.contact1.contact_id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.contact1.name)
        # Check that the form has the contact pre-selected
        form = response.context['form']
        self.assertEqual(form.fields['contact'].initial, self.contact1)

    def test_job_create_view_post_success(self):
        """Test successful POST request to create a new job"""
        before_creation = timezone.now()

        post_data = {
            'job_number': 'JOB-2024-TEST',
            'contact': self.contact1.contact_id,
            'description': 'Test job description',
            'customer_po_number': 'PO-12345',
            # due_date is optional
        }

        response = self.client.post(self.url, data=post_data)

        # Check that we redirect to the job detail page
        self.assertEqual(response.status_code, 302)

        # Verify the job was created
        job = Job.objects.get(job_number='JOB-2024-TEST')

        # Check all required fields
        self.assertEqual(job.contact, self.contact1)
        self.assertEqual(job.description, 'Test job description')
        self.assertEqual(job.customer_po_number, 'PO-12345')

        # Check defaults
        self.assertEqual(job.status, 'draft')  # Must start in draft
        self.assertIsNotNone(job.created_date)  # Must have timestamp
        self.assertGreaterEqual(job.created_date, before_creation)  # Must be current
        self.assertIsNone(job.due_date)
        self.assertIsNone(job.completed_date)

    def test_job_create_with_due_date(self):
        """Test creating a job with a due date"""
        due_date = timezone.now().date() + timezone.timedelta(days=7)

        post_data = {
            'job_number': 'JOB-2024-DUE',
            'contact': self.contact1.contact_id,
            'description': 'Job with due date',
            'due_date': due_date.strftime('%Y-%m-%d'),
        }

        response = self.client.post(self.url, data=post_data)
        self.assertEqual(response.status_code, 302)

        job = Job.objects.get(job_number='JOB-2024-DUE')
        self.assertIsNotNone(job.due_date)
        # Check the date matches (converted to date for comparison)
        self.assertEqual(job.due_date.date(), due_date)

    def test_job_create_missing_contact_fails(self):
        """Test that job creation fails without a contact"""
        post_data = {
            'job_number': 'JOB-2024-FAIL',
            # contact is missing
            'description': 'This should fail',
        }

        response = self.client.post(self.url, data=post_data)

        # Should not redirect (stays on form with errors)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')

        # Check form in context has errors
        form = response.context['form']
        self.assertIn('contact', form.errors)

        # Verify job was not created
        self.assertFalse(Job.objects.filter(job_number='JOB-2024-FAIL').exists())

    def test_job_create_missing_job_number_fails(self):
        """Test that job creation fails without a job number"""
        post_data = {
            # job_number is missing
            'contact': self.contact1.contact_id,
            'description': 'This should fail',
        }

        response = self.client.post(self.url, data=post_data)

        # Should not redirect (stays on form with errors)
        self.assertEqual(response.status_code, 200)

        # Check form in context has errors
        form = response.context['form']
        self.assertIn('job_number', form.errors)

    def test_job_create_from_contact_detail_link(self):
        """Test that the link from contact detail page pre-selects the contact"""
        # Simulate coming from contact detail page
        contact_detail_url = reverse('contacts:contact_detail', args=[self.contact2.contact_id])

        # Get the job creation form with pre-selected contact
        response = self.client.get(f"{self.url}?contact_id={self.contact2.contact_id}",
                                  HTTP_REFERER=contact_detail_url)

        self.assertEqual(response.status_code, 200)

        # Check that the correct contact is pre-selected
        form = response.context['form']
        self.assertEqual(form.fields['contact'].initial, self.contact2)

        # Also verify context has the initial_contact
        self.assertEqual(response.context['initial_contact'], self.contact2)

    def test_job_number_auto_generation_in_form(self):
        """Test that the form auto-generates a job number"""
        response = self.client.get(self.url)
        form = response.context['form']

        # Check that job_number field has an initial value
        initial_job_number = form.fields['job_number'].initial
        self.assertIsNotNone(initial_job_number)
        self.assertTrue(initial_job_number.startswith('JOB-'))
        self.assertIn(str(timezone.now().year), initial_job_number)

    def test_job_create_redirect_to_detail(self):
        """Test that successful creation redirects to job detail page"""
        post_data = {
            'job_number': 'JOB-2024-REDIRECT',
            'contact': self.contact1.contact_id,
            'description': 'Test redirect',
        }

        response = self.client.post(self.url, data=post_data)

        # Get the created job
        job = Job.objects.get(job_number='JOB-2024-REDIRECT')

        # Check redirect URL
        expected_url = reverse('jobs:detail', args=[job.job_id])
        self.assertRedirects(response, expected_url)

    def test_job_always_starts_in_draft_status(self):
        """Test that all new jobs start in draft status regardless of input"""
        # Even if someone tries to set a different status, it should be draft
        post_data = {
            'job_number': 'JOB-2024-DRAFT',
            'contact': self.contact1.contact_id,
            'status': 'approved',  # Try to set non-draft status
        }

        response = self.client.post(self.url, data=post_data)

        job = Job.objects.get(job_number='JOB-2024-DRAFT')
        # Must still be draft regardless of attempted status
        self.assertEqual(job.status, 'draft')