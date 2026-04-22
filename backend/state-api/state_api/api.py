"""Optional router aggregation for convenience imports."""

from state_api.checkpoints import router as checkpoint_router
from state_api.leases import router as lease_router

__all__ = ["checkpoint_router", "lease_router"]
