from imap_tools import MailBox, AND
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import EmailRecord, TempEmail, Configuration


class EmailService:
    """
    Service class for managing email integration via IMAP.
    Handles fetching emails, storing metadata, and retrieving full content on-demand.
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
        Fetch emails from IMAP server from the last N days and store metadata.

        Args:
            days_back (int): Number of days back to fetch emails from

        Returns:
            dict: Statistics about emails fetched (new, existing, errors)
        """
        if not self._validate_config():
            raise ValueError("Email configuration incomplete. Check settings for IMAP server, user, and password.")

        stats = {'new': 0, 'existing': 0, 'errors': []}

        try:
            with MailBox(self.imap_server).login(self.email, self.password) as mailbox:
                mailbox.folder.set(self.mailbox_folder)

                # Calculate date threshold
                date_threshold = timezone.now() - timedelta(days=days_back)

                # Fetch emails from the last N days
                for msg in mailbox.fetch(AND(date_gte=date_threshold.date())):
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
                config = Configuration.objects.first()
                retention_days = config.email_retention_days if config else 90
            except Exception:
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
