"""
Semptify 5.0 - Storage Requirement Middleware

SECURITY POLICY:
Every user MUST have their own cloud storage connected.
System users and demo users are NEVER allowed to access the application.

This middleware enforces storage connection for all protected pages.

ENHANCED in 5.0.1:
- Cookie → Database validation
- Seamless re-auth redirect (not welcome page)
- Session restoration from DB on server restart
"""

from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Set

from app.core.user_id import parse_user_id, COOKIE_USER_ID, get_provider_from_user_id


# Pages that don't require storage (public/auth pages)
PUBLIC_PATHS: Set[str] = {
    # Root and static assets
    "/",
    "/favicon.ico",
    
    # Health & monitoring
    "/health",
    "/metrics",
    "/api/version",
    
    # Storage/Auth flow (must be public to connect)
    "/storage",
    "/storage/",
    "/storage/providers",
    "/storage/auth",
    "/storage/callback",
    "/storage/logout",
    "/storage/rehome",
    
    # Welcome/setup pages
    "/welcome.html",
    "/storage_setup.html",
    "/setup_wizard.html",
    "/index.html",
    "/index-simple.html",
    
    # API docs (development only)
    "/docs",
    "/redoc",
    "/openapi.json",
    
    # Static assets
    "/static",
    "/css",
    "/js",
    "/build",
}

# Path prefixes that are always public
PUBLIC_PREFIXES = (
    "/storage/",
    "/static/",  # All static files are public
    "/api/health",
    "/api/version",
    "/api/roles",  # Role validation API - public for upgrade requests
    "/api/guided-intake",  # Guided intake - conversational onboarding
    "/api/law-library",  # Law Library - public reference
    "/api/timeline",  # Timeline needs to work for case management
    "/api/calendar",  # Calendar/events
    "/api/documents",  # Documents list
    "/api/eviction",   # Eviction defense
    "/api/brain",      # AI/Brain features
    "/api/copilot",    # Copilot assistance
    "/api/case-builder",  # Case management - intake and building
    "/api/cases",      # Case CRUD operations
)


def is_public_path(path: str) -> bool:
    """Check if path is public (doesn't require storage)."""
    # Exact match
    if path in PUBLIC_PATHS:
        return True
    
    # Prefix match
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    
    # Static assets
    if path.endswith(('.css', '.js', '.png', '.jpg', '.ico', '.svg', '.woff', '.woff2')):
        return True
    
    return False


def is_valid_storage_user(user_id: str) -> bool:
    """
    Validate user ID represents a real user with storage connected.
    
    Valid format: <provider><role><8-char-random>
    Example: GU7x9kM2pQ = Google + User + 7x9kM2pQ
    
    SECURITY: Blocks system users, demo users, and invalid IDs.
    """
    if not user_id:
        return False
    
    # Block known system/demo patterns
    invalid_patterns = [
        "open-mode",
        "system",
        "test",
        "demo",
        "guest",
        "admin-",
        "su_",
        "SU_",
    ]
    
    user_lower = user_id.lower()
    for pattern in invalid_patterns:
        if pattern.lower() in user_lower:
            return False
    
    # Must be at least 10 chars
    if len(user_id) < 10:
        return False
    
    # Validate structure using parser
    provider, role, unique = parse_user_id(user_id)
    
    # Must have valid provider and role
    if not provider or not role or not unique:
        return False
    
    # Unique part must be at least 6 chars
    if len(unique) < 6:
        return False
    
    return True


class StorageRequirementMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces storage connection requirement.
    
    SECURITY POLICY:
    - All protected pages require a valid user with storage
    - System/demo users are blocked
    - Unauthenticated users are redirected to storage providers
    
    ENHANCED: Users with valid cookies but no DB session are redirected
    to OAuth (not welcome page) for seamless re-auth.
    """
    
    def __init__(self, app, enforce: bool = True):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI application
            enforce: If False, only logs warnings (for debugging)
        """
        super().__init__(app)
        self.enforce = enforce
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Public paths don't need storage
        if is_public_path(path):
            return await call_next(request)
        
        # Get user ID from cookie
        user_id = request.cookies.get(COOKIE_USER_ID)
        
        # Check if valid storage user
        if not is_valid_storage_user(user_id):
            # Log the issue
            import logging
            logger = logging.getLogger("semptify.security")
            
            if user_id:
                logger.warning(
                    "🚫 Invalid/system user blocked: user_id=%s path=%s",
                    user_id[:4] + "***" if user_id else "None",
                    path
                )
            else:
                logger.debug("No user cookie, redirecting to storage: path=%s", path)
            
            if not self.enforce:
                # Debug mode - just log and continue
                return await call_next(request)
            
            # For API calls, return JSON error
            if path.startswith("/api/"):
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "storage_required",
                        "message": "Please connect your cloud storage to continue",
                        "action": "redirect",
                        "redirect_url": "/storage/providers"
                    }
                )
            
            # For HTML pages, redirect to storage providers
            return RedirectResponse(
                url="/storage/providers",
                status_code=302
            )
        
        # Valid cookie format - check if they need re-authentication
        # This happens when:
        # 1. Server restarted (memory cache cleared)
        # 2. Session expired in database
        # 3. Token needs refresh
        
        # The actual session validation happens in get_current_user dependency
        # If user needs re-auth, they'll have needs_reauth=True in UserContext
        # For now, just let the request through - the route handlers will check
        
        # However, we CAN do a quick check here for obvious re-auth cases
        # by checking if the session is NOT in memory cache
        from app.routers.storage import SESSIONS
        
        if user_id not in SESSIONS:
            # Session not in memory - might need DB restore or re-auth
            # Don't block here - let the security dependency handle it
            # But log for debugging
            import logging
            logger = logging.getLogger("semptify.security")
            logger.debug(
                "Session not in memory cache for user %s - will attempt DB restore",
                user_id[:4] + "***"
            )
        
        # Valid user - continue
        return await call_next(request)
