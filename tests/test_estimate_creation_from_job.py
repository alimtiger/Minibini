"""Tests for creating estimates directly from jobs"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.jobs.models import Job, Estimate
from apps.contacts.models import Contact


class EstimateCreationFromJobTests(TestCase):
    """Test creating estimates directly from job pages."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

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
            'estimate_number': 'EST-TEST001',
            'status': 'draft'
        }
        response = self.client.post(url, data)

        # Check redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Check estimate was created
        estimate = Estimate.objects.filter(job=self.job).first()
        self.assertIsNotNone(estimate)
        self.assertEqual(estimate.estimate_number, 'EST-TEST001')
        self.assertEqual(estimate.status, 'draft')
        self.assertEqual(estimate.version, 1)
        self.assertEqual(estimate.job, self.job)

    def test_estimate_versioning(self):
        """Test that versioning works when revising an estimate."""
        # Create first estimate
        url = reverse('jobs:estimate_create_for_job', args=[self.job.job_id])
        data = {
            'estimate_number': 'EST-TEST001',
            'status': 'draft'
        }
        response = self.client.post(url, data)

        # Get the created estimate and mark it as open
        estimate = Estimate.objects.filter(job=self.job).first()
        estimate.status = 'open'
        estimate.save()

        # Now revise it to create version 2
        url = reverse('jobs:estimate_revise', args=[estimate.estimate_id])
        response = self.client.post(url)

        # Check both estimates exist with correct versions
        estimates = Estimate.objects.filter(job=self.job, estimate_number='EST-TEST001').order_by('version')
        self.assertEqual(estimates.count(), 2)
        self.assertEqual(estimates[0].version, 1)
        self.assertEqual(estimates[1].version, 2)

    def test_estimate_number_prepopulation(self):
        """Test that estimate number is prepopulated correctly."""
        # Test new estimate (no existing estimates)
        url = reverse('jobs:estimate_create_for_job', args=[self.job.job_id])
        response = self.client.get(url)

        # Form should contain prepopulated estimate number
        self.assertContains(response, f'EST-{self.job.job_number}')

        # Create an estimate
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-CUSTOM',
            version=1,
            status='draft'
        )

        # Now trying to create another should redirect to existing
        response = self.client.get(url)
        # Should redirect to existing estimate
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('jobs:estimate_detail', args=[estimate.estimate_id]))