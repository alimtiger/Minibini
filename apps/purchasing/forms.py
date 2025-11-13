from django import forms
from django.core.exceptions import ValidationError
from .models import PurchaseOrder, Bill
from apps.contacts.models import Contact, Business
from apps.core.services import NumberGenerationService


class PurchaseOrderForm(forms.ModelForm):
    """Form for creating/editing PurchaseOrder"""

    class Meta:
        model = PurchaseOrder
        fields = ['job']
        help_texts = {
            'job': 'PO number will be assigned automatically on save.',
        }

    def __init__(self, *args, **kwargs):
        job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)

        # Job is optional, but if provided, pre-select it
        self.fields['job'].required = False
        if job:
            self.fields['job'].initial = job

    def save(self, commit=True):
        """Override save to generate PO number using NumberGenerationService"""
        instance = super().save(commit=False)

        # Generate the actual PO number (increments counter)
        instance.po_number = NumberGenerationService.generate_next_number('po')

        if commit:
            instance.save()
        return instance


class BillForm(forms.ModelForm):
    """Form for creating a new Bill with business or contact selection"""
    SELECTION_TYPE_CHOICES = [
        ('contact', 'Select Contact'),
        ('business', 'Select Business'),
    ]

    selection_type = forms.ChoiceField(
        choices=SELECTION_TYPE_CHOICES,
        initial='contact',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Select by'
    )

    contact = forms.ModelChoiceField(
        queryset=Contact.objects.all().select_related('business'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select Contact --"
    )

    business = forms.ModelChoiceField(
        queryset=Business.objects.all().select_related('default_contact'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select Business --",
        label='Business'
    )

    class Meta:
        model = Bill
        fields = ['purchase_order', 'vendor_invoice_number']
        widgets = {
            'purchase_order': forms.Select(attrs={'class': 'form-control'}),
            'vendor_invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        initial_contact = kwargs.pop('initial_contact', None)
        initial_business = kwargs.pop('initial_business', None)
        super().__init__(*args, **kwargs)

        # Customize contact field display to include business name
        self.fields['contact'].label_from_instance = self.label_from_instance_with_business

        # Customize business field display
        self.fields['business'].label_from_instance = self.label_from_instance_business

        # Pre-select contact or business if provided
        if initial_contact:
            self.fields['contact'].initial = initial_contact
            self.fields['selection_type'].initial = 'contact'
        elif initial_business:
            self.fields['business'].initial = initial_business
            self.fields['selection_type'].initial = 'business'

    def label_from_instance_with_business(self, contact):
        """Custom label for contact dropdown to include business name"""
        if contact.business:
            return f"{contact.name} ({contact.business.business_name})"
        return contact.name

    def label_from_instance_business(self, business):
        """Custom label for business dropdown to include default contact"""
        if business.default_contact:
            return f"{business.business_name} (Default: {business.default_contact.name})"
        return business.business_name

    def clean(self):
        """Validate that either contact or business is selected, and set contact from business if needed"""
        cleaned_data = super().clean()
        selection_type = cleaned_data.get('selection_type')
        contact = cleaned_data.get('contact')
        business = cleaned_data.get('business')

        if selection_type == 'contact':
            if not contact:
                raise ValidationError({'contact': 'Please select a contact.'})
            # Contact is directly selected, use it as-is

        elif selection_type == 'business':
            if not business:
                raise ValidationError({'business': 'Please select a business.'})
            # Set contact to business's default contact
            if not business.default_contact:
                raise ValidationError({
                    'business': f'Business "{business.business_name}" does not have a default contact set.'
                })
            cleaned_data['contact'] = business.default_contact

        return cleaned_data

    def save(self, commit=True):
        """Override save to set contact from cleaned_data"""
        instance = super().save(commit=False)

        # Set the contact from cleaned_data (may have been set from business)
        instance.contact = self.cleaned_data['contact']

        if commit:
            instance.save()
        return instance
