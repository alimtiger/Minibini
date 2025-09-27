"""
Tests for the synchronization between Estimate and Job statuses.

Business Rules:
1. Only one Estimate per job may be approved (accepted)
2. When an Estimate is approved, the Job should automatically be approved
3. An approved Estimate cannot go back to Draft (but can be superseded)
4. When an approved Estimate is superseded, the new Estimate starts in Draft and the Job becomes Blocked
5. All existing EstWorksheet-Estimate status links remain unchanged
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.jobs.models import Job, Estimate, EstWorksheet
from apps.contacts.models import Contact
from apps.core.models import User


class EstimateJobStatusSyncTest(TestCase):
    """Test the synchronization between Estimate and Job statuses."""

    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create a test contact
        self.contact = Contact.objects.create(
            name='Test Customer',
            email='customer@example.com'
        )

        # Create a test job
        self.job = Job.objects.create(
            job_number='TEST-2024-0001',
            contact=self.contact,
            description='Test job for status sync'
        )

    def test_only_one_approved_estimate_per_job(self):
        """Test that only one estimate per job can be in 'accepted' status."""
        # Create first estimate and approve it
        estimate1 = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            status='draft'
        )
        estimate1.status = 'accepted'
        estimate1.save()

        # Create second estimate
        estimate2 = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0002',
            status='draft'
        )

        # Attempt to approve second estimate should fail
        estimate2.status = 'accepted'
        with self.assertRaises(ValidationError) as context:
            estimate2.save()

        self.assertIn('already has an accepted estimate', str(context.exception))

    def test_job_auto_approved_when_estimate_approved(self):
        """Test that job status changes to 'approved' when estimate is approved."""
        # Job should start in draft
        self.assertEqual(self.job.status, 'draft')

        # Create and approve an estimate
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            status='draft'
        )

        # Change estimate to open first (following valid transition)
        estimate.status = 'open'
        estimate.save()

        # Job should still be draft
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'draft')

        # Now approve the estimate
        estimate.status = 'accepted'
        estimate.save()

        # Job should now be approved
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'approved')

    def test_approved_estimate_cannot_go_back_to_draft(self):
        """Test that an approved estimate cannot be changed back to draft status."""
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            status='draft'
        )

        # Move through valid transitions to accepted
        estimate.status = 'open'
        estimate.save()
        estimate.status = 'accepted'
        estimate.save()

        # Attempt to change back to draft should fail
        estimate.status = 'draft'
        with self.assertRaises(ValidationError) as context:
            estimate.save()

        self.assertIn('cannot transition from accepted to draft', str(context.exception).lower())

    def test_approved_estimate_can_be_superseded(self):
        """Test that an approved estimate can be superseded."""
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            status='draft'
        )

        # Move to accepted
        estimate.status = 'open'
        estimate.save()
        estimate.status = 'accepted'
        estimate.save()

        # Should be able to supersede
        estimate.status = 'superseded'
        estimate.save()  # Should not raise an exception

        self.assertEqual(estimate.status, 'superseded')

    def test_superseding_approved_estimate_blocks_job(self):
        """Test that superseding an approved estimate sets job status to blocked."""
        # Create and approve an estimate
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            status='draft'
        )
        estimate.status = 'open'
        estimate.save()
        estimate.status = 'accepted'
        estimate.save()

        # Job should be approved
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'approved')

        # Supersede the estimate
        estimate.status = 'superseded'
        estimate.save()

        # Job should now be blocked
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'blocked')

    def test_new_estimate_after_superseding_starts_in_draft(self):
        """Test that a new estimate created after superseding starts in draft."""
        # Create and approve first estimate
        estimate1 = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            version=1,
            status='draft'
        )
        estimate1.status = 'open'
        estimate1.save()
        estimate1.status = 'accepted'
        estimate1.save()

        # Supersede it
        estimate1.status = 'superseded'
        estimate1.save()

        # Create new estimate (revision)
        estimate2 = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            version=2,
            parent=estimate1,
            status='draft'  # Should start in draft
        )

        # New estimate should be in draft
        self.assertEqual(estimate2.status, 'draft')

        # Job should be blocked (from superseding the first estimate)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'blocked')

    def test_worksheet_status_sync_remains_unchanged(self):
        """Test that EstWorksheet status synchronization with Estimate still works."""
        # Create estimate with worksheet
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            status='draft'
        )

        worksheet = EstWorksheet.objects.create(
            job=self.job,
            estimate=estimate,
            status='draft'
        )

        # When estimate goes to open, worksheet should go to final
        estimate.status = 'open'
        estimate.save()

        worksheet.refresh_from_db()
        self.assertEqual(worksheet.status, 'final')

        # When estimate is accepted, worksheet should remain final
        estimate.status = 'accepted'
        estimate.save()

        worksheet.refresh_from_db()
        self.assertEqual(worksheet.status, 'final')

        # When estimate is superseded, worksheet should be superseded
        estimate.status = 'superseded'
        estimate.save()

        worksheet.refresh_from_db()
        self.assertEqual(worksheet.status, 'superseded')

    def test_job_status_changes_dont_affect_estimate(self):
        """Test that manual job status changes don't affect estimate status."""
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            status='open'
        )

        # Manually change job status
        self.job.status = 'needs_attention'
        self.job.save()

        # Estimate should remain unchanged
        estimate.refresh_from_db()
        self.assertEqual(estimate.status, 'open')

        # Change job to complete
        self.job.status = 'complete'
        self.job.save()

        # Estimate should still be unchanged
        estimate.refresh_from_db()
        self.assertEqual(estimate.status, 'open')

    def test_multiple_estimates_with_different_statuses(self):
        """Test multiple estimates on same job with different statuses."""
        # Create first estimate and reject it
        estimate1 = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            version=1,
            status='draft'
        )
        estimate1.status = 'open'
        estimate1.save()
        estimate1.status = 'rejected'
        estimate1.save()

        # Job should still be draft (rejection doesn't auto-update job)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'draft')

        # Create second estimate and approve it
        estimate2 = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0002',
            version=1,
            status='draft'
        )
        estimate2.status = 'open'
        estimate2.save()
        estimate2.status = 'accepted'
        estimate2.save()

        # Job should now be approved
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'approved')

        # First estimate should still be rejected
        estimate1.refresh_from_db()
        self.assertEqual(estimate1.status, 'rejected')

    def test_job_already_approved_remains_approved(self):
        """Test that if job is already approved, accepting an estimate keeps it approved."""
        # Manually approve the job
        self.job.status = 'approved'
        self.job.save()

        # Create and approve an estimate
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            status='draft'
        )
        estimate.status = 'open'
        estimate.save()
        estimate.status = 'accepted'
        estimate.save()

        # Job should remain approved (not cause an error)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'approved')

    def test_job_in_complete_status_not_affected(self):
        """Test that completed jobs are not affected by estimate changes."""
        # Create and approve an estimate
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            status='draft'
        )
        estimate.status = 'open'
        estimate.save()
        estimate.status = 'accepted'
        estimate.save()

        # Job should be approved
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'approved')

        # Complete the job
        self.job.status = 'complete'
        self.job.save()

        # Try to supersede the estimate
        estimate.status = 'superseded'
        estimate.save()

        # Job should remain complete (not revert to blocked)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'complete')

    def test_rejected_estimate_does_not_affect_job(self):
        """Test that rejecting an estimate doesn't change job status."""
        # Job starts in draft
        self.assertEqual(self.job.status, 'draft')

        # Create and reject an estimate
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            status='draft'
        )
        estimate.status = 'open'
        estimate.save()
        estimate.status = 'rejected'
        estimate.save()

        # Job should still be draft
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'draft')

    def test_estimate_revision_workflow(self):
        """Test the full workflow of estimate revision with job status updates."""
        # Create and approve first estimate
        estimate1 = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            version=1,
            status='draft'
        )
        estimate1.status = 'open'
        estimate1.save()
        estimate1.status = 'accepted'
        estimate1.save()

        # Job should be approved
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'approved')

        # Create revision (this typically happens through a view)
        # First, supersede the old estimate
        estimate1.status = 'superseded'
        estimate1.save()

        # Job should be blocked
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'blocked')

        # Create new version
        estimate2 = Estimate.objects.create(
            job=self.job,
            estimate_number='EST-2024-0001',
            version=2,
            parent=estimate1,
            status='draft'
        )

        # Job remains blocked while new estimate is in draft
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'blocked')

        # Open and accept the new estimate
        estimate2.status = 'open'
        estimate2.save()

        # Job still blocked (estimate not accepted yet)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'blocked')

        # Accept the new estimate
        estimate2.status = 'accepted'
        estimate2.save()

        # Job should be approved again
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'approved')