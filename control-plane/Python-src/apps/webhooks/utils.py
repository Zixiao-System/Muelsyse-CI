"""
GitHub Webhook utility functions for Muelsyse-CI

This module provides utilities for verifying GitHub webhook signatures
and other webhook-related operations.
"""
import hmac
import hashlib
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class GitHubSignatureVerifier:
    """
    Verifies GitHub webhook signatures using HMAC-SHA256.

    GitHub sends a signature in the X-Hub-Signature-256 header that can be
    used to verify the webhook payload authenticity.
    """

    SIGNATURE_HEADER = 'X-Hub-Signature-256'
    SIGNATURE_PREFIX = 'sha256='

    def __init__(self, secret: Optional[str] = None):
        """
        Initialize the verifier with a webhook secret.

        Args:
            secret: The webhook secret. If not provided, reads from settings.
        """
        self.secret = secret or self._get_default_secret()

    def _get_default_secret(self) -> str:
        """Get the default webhook secret from settings or environment."""
        return getattr(settings, 'GITHUB_WEBHOOK_SECRET', '')

    def verify(self, payload: bytes, signature: str) -> bool:
        """
        Verify the GitHub webhook signature.

        Args:
            payload: The raw request body as bytes.
            signature: The signature from X-Hub-Signature-256 header.

        Returns:
            True if the signature is valid, False otherwise.
        """
        if not self.secret:
            logger.warning("No webhook secret configured, skipping signature verification")
            return True

        if not signature:
            logger.warning("No signature provided in webhook request")
            return False

        if not signature.startswith(self.SIGNATURE_PREFIX):
            logger.warning(f"Invalid signature format: {signature[:20]}...")
            return False

        # Extract the hex digest from the signature
        provided_signature = signature[len(self.SIGNATURE_PREFIX):]

        # Compute the expected signature
        expected_signature = self._compute_signature(payload)

        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_signature, provided_signature)

        if not is_valid:
            logger.warning("Webhook signature verification failed")

        return is_valid

    def _compute_signature(self, payload: bytes) -> str:
        """
        Compute the HMAC-SHA256 signature for a payload.

        Args:
            payload: The raw request body as bytes.

        Returns:
            The hex-encoded signature.
        """
        return hmac.new(
            key=self.secret.encode('utf-8'),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()


def verify_github_signature(
    payload: bytes,
    signature: str,
    secret: Optional[str] = None
) -> bool:
    """
    Convenience function to verify a GitHub webhook signature.

    Args:
        payload: The raw request body as bytes.
        signature: The signature from X-Hub-Signature-256 header.
        secret: Optional webhook secret. Uses settings if not provided.

    Returns:
        True if the signature is valid, False otherwise.
    """
    verifier = GitHubSignatureVerifier(secret=secret)
    return verifier.verify(payload, signature)


def get_github_event_type(headers: dict) -> Optional[str]:
    """
    Extract the GitHub event type from request headers.

    Args:
        headers: Dictionary of HTTP headers.

    Returns:
        The event type (e.g., 'push', 'pull_request') or None.
    """
    return headers.get('X-GitHub-Event') or headers.get('HTTP_X_GITHUB_EVENT')


def get_github_delivery_id(headers: dict) -> Optional[str]:
    """
    Extract the GitHub delivery ID from request headers.

    Args:
        headers: Dictionary of HTTP headers.

    Returns:
        The unique delivery ID or None.
    """
    return headers.get('X-GitHub-Delivery') or headers.get('HTTP_X_GITHUB_DELIVERY')
