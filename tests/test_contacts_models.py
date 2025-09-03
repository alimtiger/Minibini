from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.contacts.models import Contact, Business, PaymentTerms


class ContactModelTest(TestCase):
    def test_contact_creation(self):
        contact = Contact.objects.create(
            name="John Doe",
            email="john@example.com",
            addr1="123 Main St",
            city="City",
            municipality="ST",
            postal_code="12345",
            mobile_number="555-123-4567"
        )
        self.assertEqual(contact.name, "John Doe")
        self.assertEqual(contact.email, "john@example.com")
        self.assertEqual(contact.address(), "123 Main St, City, ST 12345")
        self.assertEqual(contact.mobile_number, "555-123-4567")

    def test_contact_str_method(self):
        contact = Contact.objects.create(name="Jane Smith")
        self.assertEqual(str(contact), "Jane Smith")

    def test_contact_optional_fields(self):
        contact = Contact.objects.create(name="Basic Contact")
        self.assertEqual(contact.email, "")
        self.assertEqual(contact.address(), "")
        self.assertEqual(contact.mobile_number, "")

    def test_contact_email_validation(self):
        contact = Contact(
            name="Test User",
            email="invalid-email"
        )
        with self.assertRaises(ValidationError):
            contact.full_clean()


class PaymentTermsModelTest(TestCase):
    def test_payment_terms_creation(self):
        terms = PaymentTerms.objects.create()
        self.assertIsNotNone(terms.term_id)

    def test_payment_terms_meta(self):
        self.assertEqual(PaymentTerms._meta.verbose_name, "Payment Terms")
        self.assertEqual(PaymentTerms._meta.verbose_name_plural, "Payment Terms")


class BusinessModelTest(TestCase):
    def setUp(self):
        self.payment_terms = PaymentTerms.objects.create()

    def test_business_creation(self):
        business = Business.objects.create(
            our_reference_code="REF001",
            business_name="Acme Corporation",
            business_address="456 Business Ave, Suite 100",
            business_number="123-456-7890",
            tax_exemption_number="TAX123456",
            tax_cloud="CLOUD789",
            terms=self.payment_terms
        )
        self.assertEqual(business.our_reference_code, "REF001")
        self.assertEqual(business.business_name, "Acme Corporation")
        self.assertEqual(business.business_address, "456 Business Ave, Suite 100")
        self.assertEqual(business.business_number, "123-456-7890")
        self.assertEqual(business.tax_exemption_number, "TAX123456")
        self.assertEqual(business.tax_cloud, "CLOUD789")
        self.assertEqual(business.terms, self.payment_terms)

    def test_business_str_method(self):
        business = Business.objects.create(business_name="Test Business")
        self.assertEqual(str(business), "Test Business")

    def test_business_optional_fields(self):
        business = Business.objects.create(business_name="Simple Business")
        self.assertEqual(business.our_reference_code, "")
        self.assertEqual(business.business_address, "")
        self.assertEqual(business.business_number, "")
        self.assertEqual(business.tax_exemption_number, "")
        self.assertEqual(business.tax_cloud, "")
        self.assertIsNone(business.terms)

    def test_business_with_payment_terms_deletion(self):
        business = Business.objects.create(
            business_name="Test Business",
            terms=self.payment_terms
        )
        self.payment_terms.delete()
        business.refresh_from_db()
        self.assertIsNone(business.terms)
