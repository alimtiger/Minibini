from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.core.models import User, Role, Configuration


class UserModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(
            role_name="Test Role",
            role_description="A test role"
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
        
    def test_user_with_role(self):
        user = User.objects.create_user(
            username="testuser",
            role_id=self.role
        )
        self.assertEqual(user.role_id, self.role)
        
    def test_user_str_method(self):
        user = User.objects.create_user(username="testuser")
        self.assertEqual(str(user), "testuser")


class RoleModelTest(TestCase):
    def test_role_creation(self):
        role = Role.objects.create(
            role_name="Manager",
            role_description="Management role with elevated permissions"
        )
        self.assertEqual(role.role_name, "Manager")
        self.assertEqual(role.role_description, "Management role with elevated permissions")
        
    def test_role_str_method(self):
        role = Role.objects.create(role_name="Admin")
        self.assertEqual(str(role), "Admin")
        
    def test_role_optional_description(self):
        role = Role.objects.create(role_name="Basic User")
        self.assertEqual(role.role_description, "")


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