"""
Tests for contact deletion functionality.

This test suite covers:
- Validation preventing deletion of contacts associated with Jobs or Bills
- Successful deletion of contacts with no associations
- Automatic default contact reassignment when deleting the default
- Default contact clearing when deleting the last contact
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.contacts.models import Contact, Business
from apps.jobs.models import Job
from apps.purchasing.models import Bill, PurchaseOrder


class ContactDeletionValidationTest(TestCase):
    """Test validation that prevents deletion of contacts with associations"""

    def setUp(self):
        self.client = Client()
        self.business = Business.objects.create(business_name='Test Business')

        self.contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=self.business
        )

    def test_cannot_delete_contact_with_job(self):
        """Contact associated with a Job cannot be deleted"""
        # Create a job associated with the contact
        job = Job.objects.create(
            job_number='TEST-001',
            name='Test Job',
            contact=self.contact
        )

        url = reverse('contacts:delete_contact', args=[self.contact.contact_id])
        response = self.client.post(url)

        # Should redirect back to contact detail with error
        self.assertEqual(response.status_code, 302)

        # Contact should still exist
        self.assertTrue(Contact.objects.filter(contact_id=self.contact.contact_id).exists())

        # Follow redirect and check for error message
        response = self.client.post(url, follow=True)
        self.assertContains(response, 'Cannot delete contact')
        self.assertContains(response, 'Jobs:')
        self.assertContains(response, 'TEST-001')

    def test_cannot_delete_contact_with_bill(self):
        """Contact associated with a Bill cannot be deleted"""
        # Create a purchase order
        po = PurchaseOrder.objects.create(po_number='PO-001')

        # Create a bill associated with the contact
        bill = Bill.objects.create(
            purchase_order=po,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )

        url = reverse('contacts:delete_contact', args=[self.contact.contact_id])
        response = self.client.post(url, follow=True)

        # Should show error
        self.assertContains(response, 'Cannot delete contact')
        self.assertContains(response, 'Bills:')

        # Contact should still exist
        self.assertTrue(Contact.objects.filter(contact_id=self.contact.contact_id).exists())

    def test_cannot_delete_contact_with_multiple_associations(self):
        """Contact with multiple associations should show all in error message"""
        # Create both a job and a bill
        job = Job.objects.create(
            job_number='TEST-001',
            name='Test Job',
            contact=self.contact
        )

        po = PurchaseOrder.objects.create(po_number='PO-001')
        bill = Bill.objects.create(
            purchase_order=po,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )

        url = reverse('contacts:delete_contact', args=[self.contact.contact_id])
        response = self.client.post(url, follow=True)

        # Should show error with both associations
        self.assertContains(response, 'Cannot delete contact')
        self.assertContains(response, 'Jobs:')
        self.assertContains(response, 'TEST-001')
        self.assertContains(response, 'Bills:')

        # Contact should still exist
        self.assertTrue(Contact.objects.filter(contact_id=self.contact.contact_id).exists())


class ContactDeletionSuccessTest(TestCase):
    """Test successful contact deletion scenarios"""

    def setUp(self):
        self.client = Client()

    def test_delete_contact_with_no_associations(self):
        """Contact with no associations can be deleted successfully"""
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001'
        )

        contact_id = contact.contact_id
        url = reverse('contacts:delete_contact', args=[contact_id])
        response = self.client.post(url)

        # Should redirect to contact list
        self.assertEqual(response.status_code, 302)

        # Contact should be deleted
        self.assertFalse(Contact.objects.filter(contact_id=contact_id).exists())

    def test_delete_contact_with_business_no_other_associations(self):
        """Contact with business but no Jobs/Bills can be deleted"""
        business = Business.objects.create(business_name='Test Business')
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business
        )

        contact_id = contact.contact_id
        url = reverse('contacts:delete_contact', args=[contact_id])
        response = self.client.post(url)

        # Should redirect to business detail
        self.assertEqual(response.status_code, 302)

        # Contact should be deleted
        self.assertFalse(Contact.objects.filter(contact_id=contact_id).exists())

    def test_delete_redirects_to_business_detail_when_has_business(self):
        """Deleting contact with business should redirect to business detail"""
        business = Business.objects.create(business_name='Test Business')
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business
        )

        url = reverse('contacts:delete_contact', args=[contact.contact_id])
        response = self.client.post(url)

        expected_redirect = reverse('contacts:business_detail', args=[business.business_id])
        self.assertRedirects(response, expected_redirect)

    def test_delete_redirects_to_contact_list_when_no_business(self):
        """Deleting contact without business should redirect to contact list"""
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001'
        )

        url = reverse('contacts:delete_contact', args=[contact.contact_id])
        response = self.client.post(url)

        expected_redirect = reverse('contacts:contact_list')
        self.assertRedirects(response, expected_redirect)

    def test_get_request_does_not_delete(self):
        """GET request to delete_contact should not delete the contact"""
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001'
        )

        url = reverse('contacts:delete_contact', args=[contact.contact_id])
        response = self.client.get(url)

        # Should redirect without deleting
        self.assertEqual(response.status_code, 302)

        # Contact should still exist
        self.assertTrue(Contact.objects.filter(contact_id=contact.contact_id).exists())


class DefaultContactReassignmentOnDeletionTest(TestCase):
    """Test automatic default contact reassignment when deleting default"""

    def setUp(self):
        self.client = Client()
        self.business = Business.objects.create(business_name='Test Business')

    def test_delete_default_contact_shows_selection_form(self):
        """Deleting default contact with multiple others should show selection form"""
        # Create contacts
        contact_alice = Contact.objects.create(
            first_name='Alice',
            last_name='Alpha',
            email='alice@test.com',
            work_number='555-0001',
            business=self.business
        )

        contact_bob = Contact.objects.create(
            first_name='Bob',
            last_name='Beta',
            email='bob@test.com',
            work_number='555-0002',
            business=self.business
        )

        contact_charlie = Contact.objects.create(
            first_name='Charlie',
            last_name='Gamma',
            email='charlie@test.com',
            work_number='555-0003',
            business=self.business
        )

        # Set Alice as default manually
        self.business.default_contact = contact_alice
        self.business.save()

        # Try to delete Alice without selecting new default
        url = reverse('contacts:delete_contact', args=[contact_alice.contact_id])
        response = self.client.post(url)

        # Should show selection form (200 response, not redirect)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select New Default Contact')
        self.assertContains(response, 'Bob Beta')
        self.assertContains(response, 'Charlie Gamma')

        # Contact should not be deleted yet
        self.assertTrue(Contact.objects.filter(contact_id=contact_alice.contact_id).exists())

    def test_delete_default_contact_with_selection(self):
        """Deleting default contact with new default selected should work"""
        # Create contacts
        contact_alice = Contact.objects.create(
            first_name='Alice',
            last_name='Alpha',
            email='alice@test.com',
            work_number='555-0001',
            business=self.business
        )

        contact_bob = Contact.objects.create(
            first_name='Bob',
            last_name='Beta',
            email='bob@test.com',
            work_number='555-0002',
            business=self.business
        )

        contact_charlie = Contact.objects.create(
            first_name='Charlie',
            last_name='Gamma',
            email='charlie@test.com',
            work_number='555-0003',
            business=self.business
        )

        # Set Alice as default
        self.business.default_contact = contact_alice
        self.business.save()

        # Delete Alice with Bob selected as new default
        url = reverse('contacts:delete_contact', args=[contact_alice.contact_id])
        response = self.client.post(url, {'new_default_contact': contact_bob.contact_id})

        # Should redirect
        self.assertEqual(response.status_code, 302)

        # Alice should be deleted
        self.assertFalse(Contact.objects.filter(contact_id=contact_alice.contact_id).exists())

        # Bob should be new default
        self.business.refresh_from_db()
        self.assertEqual(self.business.default_contact, contact_bob)

    def test_delete_default_with_one_remaining_auto_assigns(self):
        """Deleting default with only one other contact should auto-assign remaining contact"""
        contact_alice = Contact.objects.create(
            first_name='Alice',
            last_name='Alpha',
            email='alice@test.com',
            work_number='555-0001',
            business=self.business
        )

        contact_bob = Contact.objects.create(
            first_name='Bob',
            last_name='Beta',
            email='bob@test.com',
            work_number='555-0002',
            business=self.business
        )

        # Set Alice as default
        self.business.default_contact = contact_alice
        self.business.save()

        # Delete Alice (only Bob remains)
        url = reverse('contacts:delete_contact', args=[contact_alice.contact_id])
        response = self.client.post(url)

        # Should redirect (no selection needed)
        self.assertEqual(response.status_code, 302)

        # Alice should be deleted
        self.assertFalse(Contact.objects.filter(contact_id=contact_alice.contact_id).exists())

        # Bob should be auto-assigned as default
        self.business.refresh_from_db()
        self.assertEqual(self.business.default_contact, contact_bob)

    def test_delete_only_contact_clears_default(self):
        """Deleting the only contact should clear the default"""
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=self.business
        )

        self.business.refresh_from_db()
        self.assertEqual(self.business.default_contact, contact)

        # Delete the only contact
        url = reverse('contacts:delete_contact', args=[contact.contact_id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)

        # Default should be None
        self.business.refresh_from_db()
        self.assertIsNone(self.business.default_contact)

        # Business should have no contacts
        self.assertEqual(self.business.contacts.count(), 0)

    def test_delete_non_default_contact_preserves_default(self):
        """Deleting a non-default contact should not change the default"""
        contact1 = Contact.objects.create(
            first_name='Alice',
            last_name='Alpha',
            email='alice@test.com',
            work_number='555-0001',
            business=self.business
        )

        contact2 = Contact.objects.create(
            first_name='Bob',
            last_name='Beta',
            email='bob@test.com',
            work_number='555-0002',
            business=self.business
        )

        self.business.refresh_from_db()
        original_default = self.business.default_contact

        # Delete the non-default contact
        url = reverse('contacts:delete_contact', args=[contact2.contact_id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)

        # Default should remain unchanged
        self.business.refresh_from_db()
        self.assertEqual(self.business.default_contact, original_default)

    def test_delete_default_success_message_shows_new_default(self):
        """Success message should indicate which contact is now the default"""
        contact1 = Contact.objects.create(
            first_name='Alice',
            last_name='Alpha',
            email='alice@test.com',
            work_number='555-0001',
            business=self.business
        )

        contact2 = Contact.objects.create(
            first_name='Bob',
            last_name='Beta',
            email='bob@test.com',
            work_number='555-0002',
            business=self.business
        )

        contact3 = Contact.objects.create(
            first_name='Charlie',
            last_name='Gamma',
            email='charlie@test.com',
            work_number='555-0003',
            business=self.business
        )

        self.business.refresh_from_db()

        # Delete the default contact with Bob selected as new default
        url = reverse('contacts:delete_contact', args=[contact1.contact_id])
        response = self.client.post(url, {'new_default_contact': contact2.contact_id}, follow=True)

        # Check success message indicates new default
        self.assertContains(response, 'has been deleted')
        self.assertContains(response, 'Bob Beta')
        self.assertContains(response, 'is now the default contact')

    def test_delete_default_with_invalid_selection_shows_error(self):
        """Selecting invalid contact should show error and not delete"""
        contact1 = Contact.objects.create(
            first_name='Alice',
            last_name='Alpha',
            email='alice@test.com',
            work_number='555-0001',
            business=self.business
        )

        contact2 = Contact.objects.create(
            first_name='Bob',
            last_name='Beta',
            email='bob@test.com',
            work_number='555-0002',
            business=self.business
        )

        contact3 = Contact.objects.create(
            first_name='Charlie',
            last_name='Gamma',
            email='charlie@test.com',
            work_number='555-0003',
            business=self.business
        )

        # Create contact from different business
        other_business = Business.objects.create(business_name='Other Business')
        other_contact = Contact.objects.create(
            first_name='Other',
            last_name='Contact',
            email='other@test.com',
            work_number='555-9999',
            business=other_business
        )

        self.business.refresh_from_db()

        # Try to delete Alice with invalid contact selection (contact from different business)
        url = reverse('contacts:delete_contact', args=[contact1.contact_id])
        response = self.client.post(url, {'new_default_contact': other_contact.contact_id})

        # Should show error (200 response with error message)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid contact selection')

        # Alice should not be deleted
        self.assertTrue(Contact.objects.filter(contact_id=contact1.contact_id).exists())

    def test_delete_only_contact_success_message_indicates_no_default(self):
        """Success message should indicate no default when last contact deleted"""
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=self.business
        )

        url = reverse('contacts:delete_contact', args=[contact.contact_id])
        response = self.client.post(url, follow=True)

        # Check success message mentions no default
        self.assertContains(response, 'has been deleted')
        self.assertContains(response, 'no longer has a default contact')


class ContactDetailPageDeleteButtonTest(TestCase):
    """Test that contact detail page has delete button"""

    def setUp(self):
        self.client = Client()

    def test_contact_detail_page_has_delete_button(self):
        """Contact detail page should have a Delete Contact button"""
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001'
        )

        url = reverse('contacts:contact_detail', args=[contact.contact_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Contact')

    def test_delete_button_has_confirmation(self):
        """Delete button should trigger JavaScript confirmation"""
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001'
        )

        url = reverse('contacts:contact_detail', args=[contact.contact_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Check for confirmation dialog
        self.assertContains(response, 'confirmDelete')
        self.assertContains(response, 'Are you sure')
