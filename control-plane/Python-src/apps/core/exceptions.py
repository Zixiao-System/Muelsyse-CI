"""
Custom exception handling for Muelsyse-CI API
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats errors consistently.
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Standardize error response format
        error_data = {
            'error': {
                'code': response.status_code,
                'message': get_error_message(response.data),
                'details': response.data if isinstance(response.data, dict) else None,
            }
        }
        response.data = error_data

    else:
        # Handle unexpected exceptions
        logger.exception(f"Unhandled exception: {exc}")
        response = Response(
            {
                'error': {
                    'code': 500,
                    'message': 'An unexpected error occurred.',
                    'details': None,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response


def get_error_message(data):
    """Extract a human-readable error message from response data."""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return data[0] if data else 'An error occurred.'
    if isinstance(data, dict):
        if 'detail' in data:
            return data['detail']
        if 'message' in data:
            return data['message']
        # Get first error message from field errors
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
            if isinstance(value, str):
                return f"{key}: {value}"
    return 'An error occurred.'


class MuelsyseException(Exception):
    """Base exception for Muelsyse-CI."""
    default_message = "An error occurred."
    default_code = "error"

    def __init__(self, message=None, code=None, details=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = details
        super().__init__(self.message)


class TenantNotFoundError(MuelsyseException):
    default_message = "Tenant not found."
    default_code = "tenant_not_found"


class PipelineValidationError(MuelsyseException):
    default_message = "Pipeline configuration is invalid."
    default_code = "pipeline_validation_error"


class RunnerUnavailableError(MuelsyseException):
    default_message = "No available runner found."
    default_code = "runner_unavailable"


class SecretEncryptionError(MuelsyseException):
    default_message = "Failed to encrypt/decrypt secret."
    default_code = "secret_encryption_error"
