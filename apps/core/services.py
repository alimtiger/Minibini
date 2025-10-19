"""
Service classes for core application functionality.
"""

from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Configuration


class NumberGenerationService:
    """
    Service for generating sequential document numbers using Configuration key-value pairs.

    Supports patterns like:
    - "JOB-{year}-{counter:04d}" -> JOB-2025-0001
    - "INV-{year}-{month:02d}-{counter:05d}" -> INV-2025-10-00001
    - "EST-{counter:04d}" -> EST-0001

    Thread-safe using database-level locking. Numbers are assigned atomically
    when generate_next_number() is called.

    Configuration keys:
    - job_number_sequence: Pattern for job numbers
    - job_counter: Current counter for jobs
    - estimate_number_sequence: Pattern for estimate numbers
    - estimate_counter: Current counter for estimates
    - invoice_number_sequence: Pattern for invoice numbers
    - invoice_counter: Current counter for invoices
    - po_number_sequence: Pattern for PO numbers
    - po_counter: Current counter for POs
    - bill_number_sequence: Pattern for bill numbers
    - bill_counter: Current counter for bills
    """

    # Map document types to their configuration key names
    SEQUENCE_KEYS = {
        'job': 'job_number_sequence',
        'estimate': 'estimate_number_sequence',
        'invoice': 'invoice_number_sequence',
        'po': 'po_number_sequence',
        'bill': 'bill_number_sequence',
    }

    COUNTER_KEYS = {
        'job': 'job_counter',
        'estimate': 'estimate_counter',
        'invoice': 'invoice_counter',
        'po': 'po_counter',
        'bill': 'bill_counter',
    }

    @classmethod
    def generate_next_number(cls, document_type: str) -> str:
        """
        Generate the next sequential number for the given document type.

        Args:
            document_type: One of 'job', 'estimate', 'invoice', 'po', 'bill'

        Returns:
            The next formatted document number

        Raises:
            ValidationError: If document_type is invalid or configuration is missing
        """
        if document_type not in cls.SEQUENCE_KEYS:
            raise ValidationError(
                f"Invalid document_type '{document_type}'. "
                f"Must be one of: {', '.join(cls.SEQUENCE_KEYS.keys())}"
            )

        sequence_key = cls.SEQUENCE_KEYS[document_type]
        counter_key = cls.COUNTER_KEYS[document_type]

        with transaction.atomic():
            # Get the pattern
            try:
                pattern_config = Configuration.objects.get(key=sequence_key)
                pattern = pattern_config.value
            except Configuration.DoesNotExist:
                raise ValidationError(
                    f"Configuration key '{sequence_key}' not found. "
                    "Please create it in the admin interface."
                )

            if not pattern:
                raise ValidationError(
                    f"No sequence pattern configured for {document_type}. "
                    f"Please set value for key '{sequence_key}'."
                )

            # Lock and increment the counter
            try:
                counter_config = Configuration.objects.select_for_update().get(key=counter_key)
                current_counter = int(counter_config.value or '0')
            except Configuration.DoesNotExist:
                raise ValidationError(
                    f"Configuration key '{counter_key}' not found. "
                    "Please create it in the admin interface."
                )

            next_counter = current_counter + 1
            counter_config.value = str(next_counter)
            counter_config.save()

            # Generate the number using the pattern
            number = cls._format_number(pattern, next_counter)

            return number

    @classmethod
    def _format_number(cls, pattern: str, counter: int) -> str:
        """
        Format a number using the pattern template.

        Supports placeholders:
        - {year} - 4-digit year
        - {month:02d} - 2-digit month with leading zero
        - {day:02d} - 2-digit day with leading zero
        - {counter:04d} - counter with specified formatting (e.g., 0001)
        - {counter} - counter with no formatting

        Args:
            pattern: The pattern template string
            counter: The counter value to use

        Returns:
            The formatted number string
        """
        now = datetime.now()

        # Build a context dict with available variables
        context = {
            'year': now.year,
            'month': now.month,
            'day': now.day,
            'counter': counter,
        }

        # Format the string using the pattern
        try:
            formatted = pattern.format(**context)
        except (KeyError, ValueError) as e:
            # If pattern is invalid, return a safe fallback
            formatted = f"{counter:04d}"

        return formatted

    @classmethod
    def reset_counter(cls, document_type: str, new_value: int = 0):
        """
        Reset a counter to a specific value. Use with caution!

        Args:
            document_type: One of 'job', 'estimate', 'invoice', 'po', 'bill'
            new_value: The value to reset the counter to (default: 0)
        """
        if document_type not in cls.COUNTER_KEYS:
            raise ValidationError(f"Invalid document_type '{document_type}'")

        counter_key = cls.COUNTER_KEYS[document_type]

        with transaction.atomic():
            counter_config = Configuration.objects.select_for_update().get(key=counter_key)
            counter_config.value = str(new_value)
            counter_config.save()
