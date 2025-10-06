"""Utilities for parsing email data."""

import re
from email.utils import parseaddr


def parse_email_address(from_header):
    """
    Parse email From header to extract name and email address.

    Args:
        from_header (str): Email From header (e.g., "John Doe <john@example.com>")

    Returns:
        tuple: (name, email_address)

    Example:
        >>> parse_email_address("John Doe <john@example.com>")
        ('John Doe', 'john@example.com')
    """
    if not from_header:
        return ('', '')

    name, email = parseaddr(from_header)

    # If no name found, try to extract from email
    if not name and email:
        # Use part before @ as name
        name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()

    return (name.strip(), email.strip())


def extract_company_from_signature(email_text):
    """
    Attempt to extract company name from email signature.

    This is a heuristic approach looking for common signature patterns.

    Args:
        email_text (str): Full email text content

    Returns:
        str: Extracted company name or empty string
    """
    if not email_text:
        return ''

    # Common signature indicators
    signature_markers = [
        r'--\s*\n',  # -- separator
        r'Best regards',
        r'Sincerely',
        r'Regards',
        r'Thank you',
        r'Thanks',
    ]

    # Find potential signature section
    signature_text = email_text
    for marker in signature_markers:
        match = re.search(marker, email_text, re.IGNORECASE)
        if match:
            # Get text after the marker
            signature_text = email_text[match.end():]
            break

    # Look for company name patterns
    # Pattern 1: "Company Name" or Company Name on its own line
    # Pattern 2: "at Company Name" or "@ Company Name"
    # Pattern 3: Lines ending with "Inc", "LLC", "Ltd", "Corp" etc

    company_patterns = [
        r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&,\.]+(?:Inc|LLC|Ltd|Corp|Co|Company|Group)\.?)',
        r'^([A-Z][A-Za-z0-9\s&,\.]+(?:Inc|LLC|Ltd|Corp|Co|Company|Group)\.?)$',
        r'^([A-Z][A-Za-z0-9\s&,\.]{3,40})$',  # Capitalized lines (likely company names)
    ]

    # Search signature section
    lines = signature_text.split('\n')
    for line in lines[:10]:  # Only check first 10 lines of signature
        line = line.strip()
        if not line or len(line) < 3:
            continue

        for pattern in company_patterns:
            match = re.search(pattern, line, re.MULTILINE)
            if match:
                company = match.group(1) if match.groups() else match.group(0)
                # Clean up
                company = company.strip()
                # Avoid names that are too long or contain email addresses
                if len(company) <= 50 and '@' not in company and '://' not in company:
                    return company

    return ''


def extract_email_body(email_content):
    """
    Extract the most relevant body content from email.

    Prefers plain text, removes signatures and quoted replies.

    Args:
        email_content (dict): Dict with 'text' and 'html' keys

    Returns:
        str: Cleaned email body
    """
    if not email_content:
        return ''

    # Prefer text over HTML
    body = email_content.get('text', '')
    if not body:
        # TODO: Could use html2text or similar to convert HTML
        body = email_content.get('html', '')

    if not body:
        return ''

    # Remove quoted replies (lines starting with >)
    lines = body.split('\n')
    cleaned_lines = []
    for line in lines:
        if line.strip().startswith('>'):
            break  # Stop at quoted content
        cleaned_lines.append(line)

    body = '\n'.join(cleaned_lines)

    # Truncate signature (common patterns)
    signature_patterns = [
        r'\n--\s*\n',
        r'\n\s*Best regards',
        r'\n\s*Sincerely',
        r'\n\s*Regards',
        r'\n\s*Thank you',
        r'\n\s*Thanks',
    ]

    for pattern in signature_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            body = body[:match.start()]
            break

    return body.strip()
