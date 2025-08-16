from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.core.models import User, Role, Configuration
from .base import FixtureTestCase


class UserModelFixtureTest(FixtureTestCase):
    """
    Test User model using fixture data loaded from unit_test_data.json
    """
    
    def test_user_exists_from_fixture(self):
        """Test that users from fixture data exist and have correct properties"""
        admin_user = User.objects.get(username="admin")
        self.assertEqual(admin_user.first_name, "Admin")
        self.assertEqual(admin_user.last_name, "User")
        self.assertEqual(admin_user.email, "admin@minibini.com")
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_staff)
        
        manager_user = User.objects.get(username="manager1")
        self.assertEqual(manager_user.first_name, "John")
        self.assertEqual(manager_user.last_name, "Manager")
        self.assertEqual(manager_user.email, "manager@minibini.com")
        self.assertFalse(manager_user.is_superuser)
        self.assertTrue(manager_user.is_staff)
        
    def test_user_role_relationships(self):
        """Test that user-role relationships work correctly with fixture data"""
        admin_user = User.objects.get(username="admin")
        admin_role = Role.objects.get(role_name="Administrator")
        self.assertEqual(admin_user.role_id, admin_role)
        
        manager_user = User.objects.get(username="manager1")
        manager_role = Role.objects.get(role_name="Manager")
        self.assertEqual(manager_user.role_id, manager_role)
        
    def test_user_contact_relationships(self):
        """Test that user-contact relationships work correctly"""
        admin_user = User.objects.get(username="admin")
        self.assertIsNotNone(admin_user.contact_id)
        self.assertEqual(admin_user.contact_id.name, "John Doe")
        
    def test_create_new_user_with_existing_role(self):
        """Test creating a new user and assigning an existing role from fixtures"""
        employee_role = Role.objects.get(role_name="Employee")
        new_user = User.objects.create_user(
            username="newemployee",
            email="employee@minibini.com",
            password="testpass123",
            role_id=employee_role
        )
        self.assertEqual(new_user.role_id, employee_role)
        self.assertEqual(new_user.username, "newemployee")


class RoleModelFixtureTest(FixtureTestCase):
    """
    Test Role model using fixture data
    """
    
    def test_roles_exist_from_fixture(self):
        """Test that all roles from fixture exist with correct data"""
        admin_role = Role.objects.get(role_name="Administrator")
        self.assertEqual(admin_role.role_description, "Full system access and administrative privileges")
        
        manager_role = Role.objects.get(role_name="Manager")
        self.assertEqual(manager_role.role_description, "Management level access with approval rights")
        
        employee_role = Role.objects.get(role_name="Employee")
        self.assertEqual(employee_role.role_description, "Standard employee access")
        
    def test_role_str_method_with_fixture_data(self):
        """Test role string representation with fixture data"""
        admin_role = Role.objects.get(role_name="Administrator")
        self.assertEqual(str(admin_role), "Administrator")
        
    def test_role_user_relationships(self):
        """Test that roles have correct user relationships"""
        admin_role = Role.objects.get(role_name="Administrator")
        admin_users = User.objects.filter(role_id=admin_role)
        self.assertEqual(admin_users.count(), 1)
        self.assertEqual(admin_users.first().username, "admin")
        
    def test_create_new_role(self):
        """Test creating a new role alongside existing fixture data"""
        new_role = Role.objects.create(
            role_name="Contractor",
            role_description="External contractor access"
        )
        self.assertEqual(new_role.role_name, "Contractor")
        self.assertEqual(Role.objects.count(), 4)  # 3 from fixture + 1 new


class ConfigurationModelFixtureTest(FixtureTestCase):
    """
    Test Configuration model using fixture data
    """
    
    def test_configurations_exist_from_fixture(self):
        """Test that configurations from fixture exist with correct data"""
        invoice_config = Configuration.objects.get(key="invoice_settings")
        self.assertEqual(invoice_config.field, "invoice_prefix")
        self.assertEqual(invoice_config.invoice_number_sequence, "INV-{year}-{counter:04d}")
        self.assertEqual(invoice_config.estimate_number_sequence, "EST-{year}-{counter:04d}")
        
        system_config = Configuration.objects.get(key="system_settings")
        self.assertEqual(system_config.field, "default_currency")
        
    def test_configuration_str_method_with_fixture_data(self):
        """Test configuration string representation with fixture data"""
        invoice_config = Configuration.objects.get(key="invoice_settings")
        self.assertEqual(str(invoice_config), "invoice_settings")
        
    def test_update_existing_configuration(self):
        """Test updating existing configuration from fixture data"""
        invoice_config = Configuration.objects.get(key="invoice_settings")
        original_sequence = invoice_config.invoice_number_sequence
        
        invoice_config.invoice_number_sequence = "INV-{year}-{month:02d}-{counter:04d}"
        invoice_config.save()
        
        updated_config = Configuration.objects.get(key="invoice_settings")
        self.assertNotEqual(updated_config.invoice_number_sequence, original_sequence)
        self.assertEqual(updated_config.invoice_number_sequence, "INV-{year}-{month:02d}-{counter:04d}")
        
    def test_create_new_configuration(self):
        """Test creating new configuration alongside existing fixture data"""
        new_config = Configuration.objects.create(
            key="email_settings",
            field="smtp_server",
            invoice_number_sequence="",
            estimate_number_sequence="",
            job_number_sequence="",
            po_number_sequence=""
        )
        self.assertEqual(new_config.key, "email_settings")
        self.assertEqual(Configuration.objects.count(), 3)  # 2 from fixture + 1 new