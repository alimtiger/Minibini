"""
Tests for default contact functionality in the contacts app.

This test suite covers:
- Automatic default contact assignment when a business has only one contact
- Default contact preservation when adding additional contacts
- Default contact reassignment when the default is removed
- Default contact clearing when all contacts are removed
"""

from django.test import TestCase
from apps.contacts.models import Contact, Business


class DefaultContactAutomaticAssignmentTest(TestCase):
    """Test automatic default contact assignment behavior"""

    def test_single_contact_auto_set_as_default(self):
        """When a business has only one contact, it should automatically be set as default"""
        business = Business.objects.create(business_name='Test Business')
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business
        )

        business.refresh_from_db()
        self.assertEqual(business.default_contact, contact)

    def test_adding_second_contact_preserves_default(self):
        """Adding a second contact should not change the existing default"""
        business = Business.objects.create(business_name='Test Business')

        # Add first contact (becomes default)
        contact1 = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business
        )
        business.refresh_from_db()
        self.assertEqual(business.default_contact, contact1)

        # Add second contact
        contact2 = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@test.com',
            work_number='555-0002',
            business=business
        )
        business.refresh_from_db()

        # Default should still be contact1
        self.assertEqual(business.default_contact, contact1)

    def test_contact_moved_to_business_becomes_default_if_only_one(self):
        """Moving a contact to a business should set it as default if it's the only one"""
        business = Business.objects.create(business_name='Test Business')

        # Create contact without business
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001'
        )

        # Move contact to business
        contact.business = business
        contact.save()

        business.refresh_from_db()
        self.assertEqual(business.default_contact, contact)

    def test_no_default_when_no_contacts(self):
        """A business with no contacts should have no default contact"""
        business = Business.objects.create(business_name='Test Business')

        self.assertIsNone(business.default_contact)


class DefaultContactReassignmentTest(TestCase):
    """Test default contact reassignment when contacts are removed"""

    def test_removing_default_contact_clears_default_when_no_others(self):
        """Removing the only contact should clear the default"""
        business = Business.objects.create(business_name='Test Business')
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business
        )

        business.refresh_from_db()
        self.assertEqual(business.default_contact, contact)

        # Remove the contact
        contact.delete()

        business.refresh_from_db()
        self.assertIsNone(business.default_contact)

    def test_removing_non_default_contact_preserves_default(self):
        """Removing a non-default contact should not affect the default"""
        business = Business.objects.create(business_name='Test Business')

        contact1 = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business
        )

        contact2 = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@test.com',
            work_number='555-0002',
            business=business
        )

        business.refresh_from_db()
        self.assertEqual(business.default_contact, contact1)

        # Remove the non-default contact
        contact2.delete()

        business.refresh_from_db()
        self.assertEqual(business.default_contact, contact1)

    def test_moving_default_contact_to_another_business(self):
        """Moving the default contact to another business should clear default (not auto-reassign)"""
        business1 = Business.objects.create(business_name='Business 1')
        business2 = Business.objects.create(business_name='Business 2')

        contact1 = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business1
        )

        contact2 = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@test.com',
            work_number='555-0002',
            business=business1
        )

        business1.refresh_from_db()
        self.assertEqual(business1.default_contact, contact1)

        # Move default contact to business2
        contact1.business = business2
        contact1.save()

        business1.refresh_from_db()
        business2.refresh_from_db()

        # Business1 should have no default (user must manually select)
        self.assertIsNone(business1.default_contact)

        # Business2 should have contact1 as default (only contact)
        self.assertEqual(business2.default_contact, contact1)


class DefaultContactUpdateMethodTest(TestCase):
    """Test the update_default_contact method on Business model"""

    def test_update_default_contact_with_one_contact(self):
        """update_default_contact should set the single contact as default"""
        business = Business.objects.create(business_name='Test Business')
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business
        )

        # Manually clear default
        business.default_contact = None
        business.save()

        # Call update method
        business.update_default_contact()

        business.refresh_from_db()
        self.assertEqual(business.default_contact, contact)

    def test_update_default_contact_with_no_contacts(self):
        """update_default_contact should clear default when no contacts exist"""
        business = Business.objects.create(business_name='Test Business')
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business
        )

        business.refresh_from_db()
        self.assertEqual(business.default_contact, contact)

        # Remove contact and update
        contact.business = None
        contact.save()

        business.update_default_contact()

        business.refresh_from_db()
        self.assertIsNone(business.default_contact)

    def test_update_default_contact_with_invalid_default(self):
        """update_default_contact should clear invalid default (user must manually select new default)"""
        business1 = Business.objects.create(business_name='Business 1')
        business2 = Business.objects.create(business_name='Business 2')

        contact1 = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business1
        )

        contact2 = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@test.com',
            work_number='555-0002',
            business=business2
        )

        # Add another contact to business1 so it has multiple contacts
        contact3 = Contact.objects.create(
            first_name='Bob',
            last_name='Smith',
            email='bob@test.com',
            work_number='555-0003',
            business=business1
        )

        # Manually set invalid default (contact from another business)
        business1.default_contact = contact2
        business1.save(update_fields=['default_contact'])

        # Update should clear invalid default
        business1.update_default_contact()

        business1.refresh_from_db()
        # Since business1 has multiple contacts, default should be None (user must select)
        self.assertIsNone(business1.default_contact)


class DefaultContactMultipleContactsTest(TestCase):
    """Test default contact behavior with multiple contacts"""

    def test_multiple_contacts_default_not_auto_changed(self):
        """With multiple contacts, default should not be automatically changed"""
        business = Business.objects.create(business_name='Test Business')

        contact1 = Contact.objects.create(
            first_name='Alice',
            last_name='Alpha',
            email='alice@test.com',
            work_number='555-0001',
            business=business
        )

        contact2 = Contact.objects.create(
            first_name='Bob',
            last_name='Beta',
            email='bob@test.com',
            work_number='555-0002',
            business=business
        )

        contact3 = Contact.objects.create(
            first_name='Charlie',
            last_name='Gamma',
            email='charlie@test.com',
            work_number='555-0003',
            business=business
        )

        business.refresh_from_db()

        # Default should be the first contact added
        self.assertEqual(business.default_contact, contact1)

        # Manually set to contact2
        business.default_contact = contact2
        business.save()

        # Add another contact
        contact4 = Contact.objects.create(
            first_name='David',
            last_name='Delta',
            email='david@test.com',
            work_number='555-0004',
            business=business
        )

        business.refresh_from_db()

        # Default should still be contact2
        self.assertEqual(business.default_contact, contact2)

    def test_default_contact_persists_across_saves(self):
        """Default contact should persist when business is saved"""
        business = Business.objects.create(business_name='Test Business')

        contact1 = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            work_number='555-0001',
            business=business
        )

        contact2 = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@test.com',
            work_number='555-0002',
            business=business
        )

        business.refresh_from_db()
        original_default = business.default_contact

        # Modify and save business
        business.business_phone = '555-9999'
        business.save()

        business.refresh_from_db()
        self.assertEqual(business.default_contact, original_default)
