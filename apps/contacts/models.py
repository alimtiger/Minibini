from django.db import models


class Contact(models.Model):
    contact_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name


class Business(models.Model):
    business_id = models.AutoField(primary_key=True)
    our_reference_code = models.CharField(max_length=50, blank=True)
    business_name = models.CharField(max_length=255)
    business_address = models.TextField(blank=True)
    business_number = models.CharField(max_length=50, blank=True)
    tax_exemption_number = models.CharField(max_length=50, blank=True)
    tax_cloud = models.CharField(max_length=100, blank=True)
    term_id = models.ForeignKey('PaymentTerms', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.business_name


class PaymentTerms(models.Model):
    term_id = models.AutoField(primary_key=True)
    # Additional fields not visible in diagram

    class Meta:
        verbose_name = "Payment Terms"
        verbose_name_plural = "Payment Terms"