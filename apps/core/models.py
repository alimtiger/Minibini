from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    user_id = models.AutoField(primary_key=True)
    contact_id = models.ForeignKey('contacts.Contact', on_delete=models.SET_NULL, null=True, blank=True)
    username_flagged_but_not_required_email = models.CharField(max_length=255, blank=True)
    encrypted_password = models.CharField(max_length=255)
    role_id = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True)


class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=100)
    role_description = models.TextField(blank=True)


class Configuration(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    field = models.CharField(max_length=255)
    invoice_number_sequence = models.CharField(max_length=50, blank=True)
    estimate_number_sequence = models.CharField(max_length=50, blank=True)
    job_number_sequence = models.CharField(max_length=50, blank=True)
    po_number_sequence = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"