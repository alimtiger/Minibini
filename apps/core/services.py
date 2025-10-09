"""
Service classes for core application functionality.
"""

from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from imap_tools import MailBox, AND
from .models import Configuration, EmailRecord, TempEmail


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
    """

    # Map document types to their configuration key names
    SEQUENCE_KEYS = {
        'job': 'job_number_sequence',
        'estimate': 'estimate_number_sequence',
        'invoice': 'invoice_number_sequence',
        'po': 'po_number_sequence',
    }

    COUNTER_KEYS = {
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
            document_type: One of 'job', 'estimate', 'invoice', 'po'
            new_value: The value to reset the counter to (default: 0)
        """
        if document_type not in cls.COUNTER_KEYS:
            raise ValidationError(f"Invalid document_type '{document_type}'")

        counter_key = cls.COUNTER_KEYS[document_type]

        with transaction.atomic():
            counter_config = Configuration.objects.select_for_update().get(key=counter_key)
            counter_config.value = str(new_value)
            counter_config.save()


class EmailService:
    """
    Service class for managing email integration via IMAP.
    Handles fetching emails, storing metadata, and retrieving full content on-demand.

    Configuration keys used:
    - email_retention_days: Number of days to retain temporary email data (default: 90)
    - latest_email_date: Most recent email date fetched from IMAP server (ISO format)
    - email_display_limit: Number of emails to display in inbox (default: 30)
    """

    def __init__(self):
        """Initialize with IMAP configuration from Django settings."""
        self.imap_server = getattr(settings, 'EMAIL_IMAP_SERVER', None)
        self.email = getattr(settings, 'EMAIL_HOST_USER', None)
        self.password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
        self.mailbox_folder = getattr(settings, 'EMAIL_IMAP_FOLDER', 'INBOX')

    def fetch_new_emails(self, mark_as_seen=False):
        """
        Fetch new emails from IMAP server and store metadata.

        Args:
            mark_as_seen (bool): Whether to mark fetched emails as seen on server

        Returns:
            dict: Statistics about emails fetched (new, existing, errors)
        """
        if not self._validate_config():
            raise ValueError("Email configuration incomplete. Check settings for IMAP server, user, and password.")

        stats = {'new': 0, 'existing': 0, 'errors': []}

        try:
            with MailBox(self.imap_server).login(self.email, self.password) as mailbox:
                mailbox.folder.set(self.mailbox_folder)

                # Fetch unseen emails
                for msg in mailbox.fetch(AND(seen=False)):
                    try:
                        # Get Message-ID from headers
                        message_id = msg.headers.get('message-id', [f'<{msg.uid}@unknown>'])[0]

                        # Check if we already have this email
                        if EmailRecord.objects.filter(message_id=message_id).exists():
                            stats['existing'] += 1
                            continue

                        # Create permanent EmailRecord
                        email_record = EmailRecord.objects.create(
                            message_id=message_id,
                            job=None,  # No automatic job linking per user request
                        )

                        # Create temporary metadata cache
                        TempEmail.objects.create(
                            email_record=email_record,
                            uid=msg.uid,
                            subject=msg.subject or '',
                            from_email=msg.from_ or 'unknown@example.com',
                            to_email=', '.join(msg.to) if msg.to else '',
                            cc_email=', '.join(msg.cc) if msg.cc else '',
                            date_sent=msg.date,
                            has_attachments=bool(msg.attachments),
                        )

                        stats['new'] += 1

                    except Exception as e:
                        # Use UID in error message if message_id not available
                        msg_identifier = msg.headers.get('message-id', [f'UID:{msg.uid}'])[0]
                        stats['errors'].append(f"Error processing {msg_identifier}: {str(e)}")

        except Exception as e:
            stats['errors'].append(f"IMAP connection error: {str(e)}")

        return stats

    def get_email_content(self, email_record_id):
        """
        Fetch full email content from IMAP server on-demand.

        Args:
            email_record_id: Primary key of EmailRecord

        Returns:
            dict: Email content including text, html, and attachments, or None if not found
        """
        if not self._validate_config():
            raise ValueError("Email configuration incomplete.")

        try:
            email_record = EmailRecord.objects.select_related('temp_data').get(
                email_record_id=email_record_id
            )
        except EmailRecord.DoesNotExist:
            return None

        # Check if we have temp data with UID
        if not hasattr(email_record, 'temp_data'):
            # No temp data - try to fetch by message_id
            return self._fetch_by_message_id(email_record.message_id)

        uid = email_record.temp_data.uid

        try:
            with MailBox(self.imap_server).login(self.email, self.password) as mailbox:
                mailbox.folder.set(self.mailbox_folder)

                # Fetch by UID
                for msg in mailbox.fetch(AND(uid=uid)):
                    return {
                        'subject': msg.subject,
                        'from': msg.from_,
                        'to': msg.to,
                        'cc': msg.cc,
                        'date': msg.date,
                        'text': msg.text,
                        'html': msg.html,
                        'attachments': [
                            {
                                'filename': att.filename,
                                'content_type': att.content_type,
                                'size': len(att.payload),
                                'payload': att.payload,
                            }
                            for att in msg.attachments
                        ],
                    }

        except Exception as e:
            # If UID fetch fails, try by message_id
            return self._fetch_by_message_id(email_record.message_id)

        return None

    def _fetch_by_message_id(self, message_id):
        """
        Fallback method to fetch email by Message-ID header.
        Used when UID is not available or has changed.
        """
        if not self._validate_config():
            return None

        try:
            with MailBox(self.imap_server).login(self.email, self.password) as mailbox:
                mailbox.folder.set(self.mailbox_folder)

                # Search by Message-ID header
                for msg in mailbox.fetch(AND(header=['Message-ID', message_id])):
                    return {
                        'subject': msg.subject,
                        'from': msg.from_,
                        'to': msg.to,
                        'cc': msg.cc,
                        'date': msg.date,
                        'text': msg.text,
                        'html': msg.html,
                        'attachments': [
                            {
                                'filename': att.filename,
                                'content_type': att.content_type,
                                'size': len(att.payload),
                                'payload': att.payload,
                            }
                            for att in msg.attachments
                        ],
                    }

        except Exception:
            pass

        return None

    def fetch_emails_by_date_range(self, days_back=30):
        """
        Fetch emails from IMAP server since latest_email_date or last N days.
        Updates latest_email_date after fetching.

        Args:
            days_back (int): Number of days back to use if latest_email_date not set

        Returns:
            dict: Statistics about emails fetched (new, existing, errors, latest_date)
        """
        if not self._validate_config():
            raise ValueError("Email configuration incomplete. Check settings for IMAP server, user, and password.")

        stats = {'new': 0, 'existing': 0, 'errors': [], 'latest_date': None}

        try:
            # Get or create latest_email_date configuration
            try:
                latest_date_config = Configuration.objects.get(key='latest_email_date')
                date_threshold = datetime.fromisoformat(latest_date_config.value)
            except Configuration.DoesNotExist:
                # Create default configuration
                date_threshold = timezone.now() - timedelta(days=days_back)
                Configuration.objects.create(
                    key='latest_email_date',
                    value=date_threshold.isoformat()
                )
            except (ValueError, AttributeError):
                # Invalid date format, reset to default
                date_threshold = timezone.now() - timedelta(days=days_back)

            # Ensure we have email_retention_days config
            try:
                Configuration.objects.get(key='email_retention_days')
            except Configuration.DoesNotExist:
                Configuration.objects.create(key='email_retention_days', value='90')

            # Ensure we have email_display_limit config
            try:
                Configuration.objects.get(key='email_display_limit')
            except Configuration.DoesNotExist:
                Configuration.objects.create(key='email_display_limit', value='30')

            most_recent_email_date = date_threshold

            with MailBox(self.imap_server).login(self.email, self.password) as mailbox:
                mailbox.folder.set(self.mailbox_folder)

                # Fetch emails since date_threshold
                for msg in mailbox.fetch(AND(date_gte=date_threshold.date())):
                    try:
                        # Get Message-ID from headers
                        message_id = msg.headers.get('message-id', [f'<{msg.uid}@unknown>'])[0]

                        # Track most recent email date
                        if msg.date and msg.date > most_recent_email_date:
                            most_recent_email_date = msg.date

                        # Check if we already have this email
                        if EmailRecord.objects.filter(message_id=message_id).exists():
                            stats['existing'] += 1
                            continue

                        # Create permanent EmailRecord
                        email_record = EmailRecord.objects.create(
                            message_id=message_id,
                            job=None,  # No automatic job linking per user request
                        )

                        # Create temporary metadata cache
                        TempEmail.objects.create(
                            email_record=email_record,
                            uid=msg.uid,
                            subject=msg.subject or '',
                            from_email=msg.from_ or 'unknown@example.com',
                            to_email=', '.join(msg.to) if msg.to else '',
                            cc_email=', '.join(msg.cc) if msg.cc else '',
                            date_sent=msg.date,
                            has_attachments=bool(msg.attachments),
                        )

                        stats['new'] += 1

                    except Exception as e:
                        # Use UID in error message if message_id not available
                        msg_identifier = msg.headers.get('message-id', [f'UID:{msg.uid}'])[0]
                        stats['errors'].append(f"Error processing {msg_identifier}: {str(e)}")

            # Update latest_email_date to most recent email found
            if most_recent_email_date > date_threshold:
                latest_date_config = Configuration.objects.get(key='latest_email_date')
                latest_date_config.value = most_recent_email_date.isoformat()
                latest_date_config.save()
                stats['latest_date'] = most_recent_email_date

        except Exception as e:
            stats['errors'].append(f"IMAP connection error: {str(e)}")

        return stats

    def cleanup_old_temp_emails(self, retention_days=None):
        """
        Delete TempEmail records older than the configured retention period.
        EmailRecord entries are preserved permanently.

        Args:
            retention_days (int): Override default retention period from configuration

        Returns:
            int: Number of TempEmail records deleted
        """
        if retention_days is None:
            # Get retention period from Configuration model
            try:
                config = Configuration.objects.get(key='email_retention_days')
                retention_days = int(config.value)
            except (Configuration.DoesNotExist, ValueError):
                retention_days = 90

        cutoff_date = timezone.now() - timedelta(days=retention_days)

        # Delete TempEmail records older than cutoff
        # EmailRecord entries remain intact
        deleted_count, _ = TempEmail.objects.filter(
            created_at__lt=cutoff_date
        ).delete()

        return deleted_count

    def link_email_to_job(self, email_record_id, job_id):
        """
        Associate an EmailRecord with a Job.

        Args:
            email_record_id: Primary key of EmailRecord
            job_id: Primary key of Job

        Returns:
            EmailRecord: Updated email record, or None if not found
        """
        try:
            email_record = EmailRecord.objects.get(email_record_id=email_record_id)
            email_record.job_id = job_id
            email_record.save()
            return email_record
        except EmailRecord.DoesNotExist:
            return None

    def _validate_config(self):
        """Check if required IMAP configuration is present."""
        return all([self.imap_server, self.email, self.password])
