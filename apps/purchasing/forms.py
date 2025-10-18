from django import forms
from .models import PurchaseOrder, PurchaseOrderLineItem
from apps.contacts.models import Business
from apps.jobs.models import Job
from apps.invoicing.models import PriceListItem
from apps.core.services import NumberGenerationService


class PurchaseOrderForm(forms.ModelForm):
    """Form for creating/editing PurchaseOrder"""
    business = forms.ModelChoiceField(
        queryset=Business.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select Business --"
    )
    job = forms.ModelChoiceField(
        queryset=Job.objects.filter(status='approved'),
        required=False,
        empty_label="-- Select Job (optional) --"
    )
    requested_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Optional delivery/completion date requested by buyer'
    )

    class Meta:
        model = PurchaseOrder
        fields = ['business', 'job', 'requested_date']

    def __init__(self, *args, **kwargs):
        job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)

        # Only show help text for job field on create (not edit)
        if self.instance and self.instance.pk:
            # Editing existing PO - no help text needed
            self.fields['job'].help_text = ''
        else:
            # Creating new PO
            self.fields['job'].help_text = 'PO number will be assigned automatically on save.'

        # If job provided, pre-select it
        if job:
            self.fields['job'].initial = job

    def save(self, commit=True):
        """Override save to generate PO number using NumberGenerationService"""
        instance = super().save(commit=False)

        # Generate the actual PO number only for new POs (increments counter)
        if not instance.pk:
            instance.po_number = NumberGenerationService.generate_next_number('po')

        if commit:
            instance.save()
        return instance


class PurchaseOrderLineItemForm(forms.Form):
    """Form for creating a PO line item from a Price List Item"""
    price_list_item = forms.ModelChoiceField(
        queryset=PriceListItem.objects.all(),
        required=True,
        label="Price List Item"
    )
    qty = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=1.0,
        widget=forms.NumberInput(attrs={'step': '0.01'}),
        label="Quantity"
    )


class PurchaseOrderStatusForm(forms.Form):
    """Form for changing PurchaseOrder status"""
    VALID_TRANSITIONS = {
        'draft': ['issued'],
        'issued': ['partly_received', 'received_in_full', 'cancelled'],
        'partly_received': ['received_in_full'],
        'received_in_full': [],  # Terminal state
        'cancelled': [],  # Terminal state
    }

    status = forms.ChoiceField(choices=[], required=True)

    def __init__(self, *args, **kwargs):
        current_status = kwargs.pop('current_status', 'draft')
        super().__init__(*args, **kwargs)

        # Set valid status choices based on current status
        valid_statuses = self.VALID_TRANSITIONS.get(current_status, [])
        # Convert status codes to display names
        from .models import PurchaseOrder
        status_dict = dict(PurchaseOrder.PO_STATUS_CHOICES)

        choices = [(current_status, f'{status_dict.get(current_status)} (current)')]
        choices.extend([(s, status_dict.get(s)) for s in valid_statuses])

        self.fields['status'].choices = choices
        self.fields['status'].initial = current_status

    @staticmethod
    def has_valid_transitions(current_status):
        """Check if the current status has any valid transitions."""
        return len(PurchaseOrderStatusForm.VALID_TRANSITIONS.get(current_status, [])) > 0

    def clean_status(self):
        """Validate that the status transition is valid."""
        return self.cleaned_data['status']
