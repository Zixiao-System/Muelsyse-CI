"""
Thread-local context for tenant isolation.
"""
import threading
from typing import Optional

_thread_locals = threading.local()


def set_current_tenant(tenant) -> None:
    """Set the current tenant in thread-local storage."""
    _thread_locals.tenant = tenant


def get_current_tenant():
    """Get the current tenant from thread-local storage."""
    return getattr(_thread_locals, 'tenant', None)


def clear_current_tenant() -> None:
    """Clear the current tenant from thread-local storage."""
    if hasattr(_thread_locals, 'tenant'):
        del _thread_locals.tenant


class TenantContext:
    """Context manager for tenant isolation."""

    def __init__(self, tenant):
        self.tenant = tenant
        self.previous_tenant = None

    def __enter__(self):
        self.previous_tenant = get_current_tenant()
        set_current_tenant(self.tenant)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_tenant:
            set_current_tenant(self.previous_tenant)
        else:
            clear_current_tenant()
        return False
