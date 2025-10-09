"""
Service classes for core application functionality.
"""

from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Configuration


class NumberGenerationService:
    """
    Service for generating sequential document numbers using Configuration patterns.

    Supports patterns like:
    - "JOB-{year}-{counter:04d}" -> JOB-2025-0001
    - "INV-{year}-{month:02d}-{counter:05d}" -> INV-2025-10-00001
    - "EST-{counter:04d}" -> EST-0001

    Thread-safe using database-level locking. Numbers are assigned atomically
    when generate_next_number() is called.
    """

    # Configuration key where numbering patterns are stored
    CONFIG_KEY = 'invoice_config'

    # Map document types to their sequence field names
    SEQUENCE_FIELDS = {
        'job': 'job_number_sequence',
        'estimate': 'estimate_number_sequence',
        'invoice': 'invoice_number_sequence',
        'po': 'po_number_sequence',
    }

    # Map document types to their counter field names
    COUNTER_FIELDS = {
        'job': 'job_counter',
        'estimate': 'estimate_counter',
        'invoice': 'invoice_counter',
        'po': 'po_counter',
    }

    @classmethod
    def generate_next_number(cls, document_type: str) -> str:
        """
        Generate the next sequential number for the given document type.

        Args:
            document_type: One of 'job', 'estimate', 'invoice', 'po'

        Returns:
            The next formatted document number

        Raises:
            ValidationError: If document_type is invalid or configuration is missing
        """
        if document_type not in cls.SEQUENCE_FIELDS:
            raise ValidationError(
                f"Invalid document_type '{document_type}'. "
                f"Must be one of: {', '.join(cls.SEQUENCE_FIELDS.keys())}"
            )

        with transaction.atomic():
            # Lock the configuration row for update
            try:
                config = Configuration.objects.select_for_update().get(key=cls.CONFIG_KEY)
            except Configuration.DoesNotExist:
                raise ValidationError(
                    f"Configuration with key '{cls.CONFIG_KEY}' not found. "
                    "Please create it in the admin interface."
                )

            # Get the sequence pattern and counter field names
            sequence_field = cls.SEQUENCE_FIELDS[document_type]
            counter_field = cls.COUNTER_FIELDS[document_type]

            # Get the pattern template
            pattern = getattr(config, sequence_field, '')
            if not pattern:
                raise ValidationError(
                    f"No sequence pattern configured for {document_type}. "
                    f"Please set {sequence_field} in Configuration."
                )

            # Increment the counter
            current_counter = getattr(config, counter_field, 0)
            next_counter = current_counter + 1
            setattr(config, counter_field, next_counter)
            config.save()

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
            document_type: One of 'job', 'estimate', 'invoice', 'po'
            new_value: The value to reset the counter to (default: 0)
        """
        if document_type not in cls.COUNTER_FIELDS:
            raise ValidationError(f"Invalid document_type '{document_type}'")

        with transaction.atomic():
            config = Configuration.objects.select_for_update().get(key=cls.CONFIG_KEY)
            counter_field = cls.COUNTER_FIELDS[document_type]
            setattr(config, counter_field, new_value)
            config.save()
