from django.db import models


class Contact(models.Model):
    contact_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
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
    our_reference_code = models.CharField(max_length=50, blank=True)
    business_name = models.CharField(max_length=255)
    business_address = models.TextField(blank=True)
    business_number = models.CharField(max_length=50, blank=True)
    tax_exemption_number = models.CharField(max_length=50, blank=True)
    tax_cloud = models.CharField(max_length=100, blank=True)
    terms = models.ForeignKey('PaymentTerms', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.business_name


class PaymentTerms(models.Model):
    term_id = models.AutoField(primary_key=True)
    # Additional fields not visible in diagram

    class Meta:
        verbose_name = "Payment Terms"
        verbose_name_plural = "Payment Terms"