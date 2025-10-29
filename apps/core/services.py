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


class LineItemService:
    """
    Service for managing line items across different container types.

    Works with any container object (Estimate, Invoice, PurchaseOrder, Bill)
    that has a 'status' field and line items inheriting from BaseLineItem.

    All operations validate that the container is in 'draft' status before
    allowing modifications, ensuring consistency across all document types.

    Example usage:
        # Delete a line item
        try:
            parent, line_num = LineItemService.delete_line_item_with_renumber(line_item)
            messages.success(request, f'Line item {line_num} deleted successfully.')
        except ValidationError as e:
            messages.error(request, str(e))

        # Reorder a line item
        try:
            parent = LineItemService.reorder_line_item(line_item, 'up')
            messages.success(request, 'Line item moved up.')
        except ValidationError as e:
            messages.error(request, str(e))
    """

    EDITABLE_STATUS = 'draft'

    @classmethod
    def can_modify_line_items(cls, container):
        """
        Check if line items can be modified on this container.

        Args:
            container: An object with a 'status' attribute (Estimate, Invoice, PO, Bill)

        Returns:
            bool: True if line items can be modified
        """
        return container.status == cls.EDITABLE_STATUS

    @classmethod
    def validate_modification(cls, container):
        """
        Validate that the container allows line item modifications.

        Args:
            container: An object with a 'status' attribute

        Raises:
            ValidationError: If modifications are not allowed
        """
        if not cls.can_modify_line_items(container):
            container_type = container.__class__.__name__
            raise ValidationError(
                f'Cannot modify line items on a {container.get_status_display().lower()} '
                f'{container_type.lower()}. Only draft {container_type.lower()}s can be modified.'
            )

    @classmethod
    def get_line_item_model(cls, line_item):
        """
        Get the model class for a line item instance.

        Args:
            line_item: An instance of a BaseLineItem subclass

        Returns:
            The model class
        """
        return line_item.__class__

    @classmethod
    def get_parent_container(cls, line_item):
        """
        Get the parent container object for a line item.

        Args:
            line_item: An instance of a BaseLineItem subclass

        Returns:
            The parent container object (Estimate, Invoice, etc.)
        """
        parent_field_name = line_item.get_parent_field_name()
        return getattr(line_item, parent_field_name)

    @classmethod
    @transaction.atomic
    def delete_line_item_with_renumber(cls, line_item):
        """
        Delete a line item and renumber remaining items in the container.

        This is the primary method for deleting line items. It:
        1. Validates the parent container is in draft status
        2. Deletes the line item
        3. Renumbers remaining line items sequentially

        Args:
            line_item: An instance of a BaseLineItem subclass

        Raises:
            ValidationError: If the parent container doesn't allow modifications

        Returns:
            tuple: (parent_container, deleted_line_number)
        """
        # Get parent container and validate
        parent_container = cls.get_parent_container(line_item)
        cls.validate_modification(parent_container)

        # Store info before deletion
        deleted_line_number = line_item.line_number
        line_item_model = cls.get_line_item_model(line_item)
        parent_field_name = line_item.get_parent_field_name()

        # Delete the line item
        line_item.delete()

        # Renumber remaining line items
        remaining_items = line_item_model.objects.filter(
            **{parent_field_name: parent_container}
        ).order_by('line_number', 'line_item_id')

        # Reassign line numbers sequentially
        for index, item in enumerate(remaining_items, start=1):
            if item.line_number != index:
                item.line_number = index
                item.save()

        return parent_container, deleted_line_number

    @classmethod
    @transaction.atomic
    def reorder_line_item(cls, line_item, direction):
        """
        Reorder a line item within its container by swapping line numbers.

        Args:
            line_item: An instance of a BaseLineItem subclass
            direction: 'up' or 'down'

        Raises:
            ValidationError: If modifications not allowed or invalid direction

        Returns:
            The parent container object
        """
        # Get parent container and validate
        parent_container = cls.get_parent_container(line_item)
        cls.validate_modification(parent_container)

        # Get all line items for this container
        line_item_model = cls.get_line_item_model(line_item)
        parent_field_name = line_item.get_parent_field_name()

        all_items = list(line_item_model.objects.filter(
            **{parent_field_name: parent_container}
        ).order_by('line_number', 'line_item_id'))

        # Find the index of the current line item
        try:
            current_index = next(
                i for i, item in enumerate(all_items)
                if item.line_item_id == line_item.line_item_id
            )
        except StopIteration:
            raise ValidationError('Line item not found in container.')

        # Determine the swap target
        if direction == 'up' and current_index > 0:
            swap_index = current_index - 1
        elif direction == 'down' and current_index < len(all_items) - 1:
            swap_index = current_index + 1
        else:
            raise ValidationError(f'Cannot move line item {direction} from current position.')

        # Swap line numbers
        current_item = all_items[current_index]
        swap_item = all_items[swap_index]
        current_item.line_number, swap_item.line_number = (
            swap_item.line_number,
            current_item.line_number
        )

        current_item.save()
        swap_item.save()

        return parent_container

    @classmethod
    def get_line_items_for_container(cls, container, line_item_model):
        """
        Get all line items for a container, ordered by line number.

        Args:
            container: The parent container object
            line_item_model: The LineItem model class

        Returns:
            QuerySet of line items ordered by line_number

        Raises:
            ValueError: If container type is not recognized
        """
        container_type = container.__class__.__name__

        # Map container types to field names
        field_name_map = {
            'Estimate': 'estimate',
            'Invoice': 'invoice',
            'PurchaseOrder': 'purchase_order',
            'Bill': 'bill'
        }

        parent_field_name = field_name_map.get(container_type)
        if not parent_field_name:
            raise ValueError(f'Unknown container type: {container_type}')

        return line_item_model.objects.filter(
            **{parent_field_name: container}
        ).order_by('line_number', 'line_item_id')

    @classmethod
    def calculate_total(cls, line_items):
        """
        Calculate the total amount for a collection of line items.

        Args:
            line_items: QuerySet or list of line items

        Returns:
            Decimal: Total amount
        """
        return sum(item.total_amount for item in line_items)
