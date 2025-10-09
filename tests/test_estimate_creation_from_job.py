"""Tests for creating estimates directly from jobs"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.jobs.models import Job, Estimate
from apps.contacts.models import Contact
from apps.core.models import Configuration


class EstimateCreationFromJobTests(TestCase):
    """Test creating estimates directly from job pages."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create Configuration for number generation
        Configuration.objects.create(
            key='invoice_config',
            field='document_numbering',
            job_number_sequence='JOB-{year}-{counter:04d}',
            estimate_number_sequence='EST-{year}-{counter:04d}',
            invoice_number_sequence='INV-{year}-{counter:04d}',
            po_number_sequence='PO-{year}-{counter:04d}',
            job_counter=0,
            estimate_counter=0,
            invoice_counter=0,
            po_counter=0
        )

        # Create a test contact
        self.contact = Contact.objects.create(
            name='Test Contact',
            email='test@example.com'
        )

        # Create a job
        self.job = Job.objects.create(
            job_number='TEST001',
            description='Test Job',
            contact=self.contact
        )

    def test_estimate_create_for_job_get(self):
        """Test GET request to create estimate for job form."""
        url = reverse('jobs:estimate_create_for_job', args=[self.job.job_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Estimate')
        self.assertContains(response, self.job.job_number)

    def test_estimate_create_for_job_post(self):
        """Test POST request to create estimate for job."""
        url = reverse('jobs:estimate_create_for_job', args=[self.job.job_id])
        data = {
            # estimate_number is auto-generated, not posted
            'status': 'draft'
        }
        response = self.client.post(url, data)

        # Check redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Check estimate was created
        estimate = Estimate.objects.filter(job=self.job).first()
        self.assertIsNotNone(estimate)
        # Verify auto-generated estimate number follows pattern
        self.assertTrue(estimate.estimate_number.startswith('EST-'))
        self.assertEqual(estimate.status, 'draft')
        self.assertEqual(estimate.version, 1)
        self.assertEqual(estimate.job, self.job)

    def test_estimate_versioning(self):
        """Test that versioning works when revising an estimate."""
        # Create first estimate
        url = reverse('jobs:estimate_create_for_job', args=[self.job.job_id])
        data = {
            # estimate_number is auto-generated
            'status': 'draft'
        }
        response = self.client.post(url, data)

        # Get the created estimate and mark it as open
        estimate = Estimate.objects.filter(job=self.job).first()
        estimate_number = estimate.estimate_number  # Store the auto-generated number
        estimate.status = 'open'
        estimate.save()

        # Now revise it to create version 2
        url = reverse('jobs:estimate_revise', args=[estimate.estimate_id])
        response = self.client.post(url)

        # Check both estimates exist with correct versions
        estimates = Estimate.objects.filter(job=self.job, estimate_number=estimate_number).order_by('version')
        self.assertEqual(estimates.count(), 2)
        self.assertEqual(estimates[0].version, 1)
        self.assertEqual(estimates[1].version, 2)

    def test_estimate_number_not_in_form(self):
        """Test that estimate number is not shown on form (assigned on save)."""
        # Test new estimate form
        url = reverse('jobs:estimate_create_for_job', args=[self.job.job_id])
        response = self.client.get(url)

        # Estimate number should NOT be in the form (it's auto-generated on save)
        self.assertNotContains(response, 'name="estimate_number"')
        # Help text should indicate auto-generation
        self.assertContains(response, 'automatically on save')