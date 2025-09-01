from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from apps.core.models import User, Configuration
from apps.contacts.models import Contact


class UserModelTest(TestCase):
    def setUp(self):
        self.group = Group.objects.create(
            name="Test Group"
        )
        
    def test_user_creation(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpassword123"))
        
    def test_user_with_group(self):
        user = User.objects.create_user(
            username="testuser"
        )
        user.groups.add(self.group)
        self.assertIn(self.group, user.groups.all())
        
    def test_user_str_method(self):
        user = User.objects.create_user(username="testuser")
        self.assertEqual(str(user), "testuser")
    
    def test_user_contact_unique_constraint(self):
        """Test that each Contact can be associated with at most one User"""
        # Create a contact
        contact = Contact.objects.create(
            name="John Doe",
            email="john@example.com"
        )
        
        # Create first user with the contact - should work
        user1 = User.objects.create_user(
            username="user1",
            contact=contact
        )
        self.assertEqual(user1.contact, contact)
        
        # Try to create second user with same contact - should raise IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username="user2", 
                    contact=contact
                )
        
        # Verify first user still exists and has the contact (after transaction rollback)
        user1.refresh_from_db()
        self.assertEqual(user1.contact, contact)
        
        # Test that users can exist without contacts (should still work)
        user3 = User.objects.create_user(username="user3")
        self.assertIsNone(user3.contact)
        
        # Test that multiple users can have no contact (null values are allowed)
        user4 = User.objects.create_user(username="user4")
        self.assertIsNone(user4.contact)


class GroupModelTest(TestCase):
    def test_group_creation(self):
        group = Group.objects.create(name="Manager")
        
        self.assertEqual(group.name, "Manager")
        self.assertEqual(str(group), "Manager")
        
    def test_group_str_method(self):
        group = Group.objects.create(name="Admin")
        self.assertEqual(str(group), "Admin")
        
    def test_user_group_assignment(self):
        group = Group.objects.create(name="Employee")
        user = User.objects.create_user(username="testuser")
        
        user.groups.add(group)
        self.assertIn(group, user.groups.all())
        self.assertIn(user, group.user_set.all())


class ConfigurationModelTest(TestCase):
    def test_configuration_creation(self):
        config = Configuration.objects.create(
            key="invoice_settings",
            field="invoice_prefix",
            invoice_number_sequence="INV-{year}-{counter:04d}",
            estimate_number_sequence="EST-{year}-{counter:04d}",
            job_number_sequence="JOB-{year}-{counter:04d}",
            po_number_sequence="PO-{year}-{counter:04d}"
        )
        self.assertEqual(config.key, "invoice_settings")
        self.assertEqual(config.field, "invoice_prefix")
        self.assertEqual(config.invoice_number_sequence, "INV-{year}-{counter:04d}")
        
    def test_configuration_str_method(self):
        config = Configuration.objects.create(key="test_key", field="test_field")
        self.assertEqual(str(config), "test_key")
        
    def test_configuration_optional_sequences(self):
        config = Configuration.objects.create(key="basic_config", field="basic_field")
        self.assertEqual(config.invoice_number_sequence, "")
        self.assertEqual(config.estimate_number_sequence, "")
        self.assertEqual(config.job_number_sequence, "")
        self.assertEqual(config.po_number_sequence, "")