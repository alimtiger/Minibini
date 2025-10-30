from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator


class Contact(models.Model):
    contact_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    middle_initial = models.CharField(max_length=10, blank=True)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(validators=[EmailValidator()])
    addr1 = models.CharField(max_length=255, blank=True)
    addr2 = models.CharField(max_length=255, blank=True)
    addr3 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    municipality = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country_code = models.CharField(max_length=3, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    work_number = models.CharField(max_length=20, blank=True)
    home_number = models.CharField(max_length=20, blank=True)
    business = models.ForeignKey('Business', on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts')

    def __str__(self):
        return self.name

    @property
    def name(self):
        """Combine name parts with proper spacing"""
        parts = [self.first_name]
        if self.middle_initial:
            parts.append(self.middle_initial)
        parts.append(self.last_name)
        return ' '.join(parts)

    def clean(self):
        """Validate that email and at least one phone number is provided"""
        # Validate email is not empty
        if not self.email or not self.email.strip():
            raise ValidationError('Email address is required.')

        # Validate at least one phone number is provided
        if not any([self.work_number, self.mobile_number, self.home_number]):
            raise ValidationError('At least one phone number (work, mobile, or home) is required.')

    def phone(self):
        # Return highest priority phone number: work > mobile > home
        if self.work_number:
            return self.work_number
        elif self.mobile_number:
            return self.mobile_number
        elif self.home_number:
            return self.home_number
        return ""

    def address(self):
        # Return complete address if all components available
        if (self.addr1 and self.city and self.postal_code):
            municipality_part = f", {self.municipality}" if self.municipality else ""
            return f"{self.addr1}, {self.city}{municipality_part} {self.postal_code}"
        # Return just addr1 if that's all we have
        elif self.addr1:
            return self.addr1
        return ""


class Business(models.Model):
    business_id = models.AutoField(primary_key=True)
    our_reference_code = models.CharField(max_length=50, blank=True, unique=True)
    business_name = models.CharField(max_length=255)
    business_address = models.TextField(blank=True)
    business_phone = models.CharField(max_length=20, blank=True)
    tax_exemption_number = models.CharField(max_length=50, blank=True)
    website = models.URLField(max_length=200, blank=True)
    terms = models.ForeignKey('PaymentTerms', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        # Auto-generate reference code if not provided
        if not self.our_reference_code:
            # Get the latest business to determine the next number
            last_business = Business.objects.order_by('-business_id').first()
            if last_business and last_business.business_id:
                next_id = last_business.business_id + 1
            else:
                next_id = 1

            # Generate reference code in format BUS-0001, BUS-0002, etc.
            self.our_reference_code = f"BUS-{next_id:04d}"

            # Check if this reference code already exists (race condition protection)
            while Business.objects.filter(our_reference_code=self.our_reference_code).exists():
                next_id += 1
                self.our_reference_code = f"BUS-{next_id:04d}"

        super().save(*args, **kwargs)


class PaymentTerms(models.Model):
    term_id = models.AutoField(primary_key=True)
    # Additional fields not visible in diagram

    class Meta:
        verbose_name = "Payment Terms"
        verbose_name_plural = "Payment Terms"