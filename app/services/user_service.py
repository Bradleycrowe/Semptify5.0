"""
Semptify 5.0 - User Service
Handles user persistence, lookup, and provider management.

╔══════════════════════════════════════════════════════════════════════════════╗
║                         PRIVACY FIRST DESIGN                                 ║
║                                                                              ║
║  SEMPTIFY NEVER STORES PERSONAL DATA. This includes:                         ║
║  - No email addresses                                                        ║
║  - No names (first, last, display)                                          ║
║  - No phone numbers, addresses, or any PII                                  ║
║                                                                              ║
║  User identity = anonymous random ID                                         ║
║  User data = stored in THEIR cloud storage                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Solves the "returning user" problem:
1. Where to look for token? → Check user's primary_provider
2. What role to load? → Check user's default_role
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, LinkedProvider
from app.core.database import get_db_session
from app.core.utc import utc_now


# =============================================================================
# User CRUD Operations
# =============================================================================

async def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by their internal ID."""
    async with get_db_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


async def get_user_by_provider(provider: str, storage_user_id: str) -> Optional[User]:
    """Get user by storage provider identity."""
    from app.core.security import derive_user_id
    user_id = derive_user_id(provider, storage_user_id)
    return await get_user_by_id(user_id)


async def create_user(
    user_id: str,
    provider: str,
    storage_user_id: str,
    default_role: str = "tenant",
) -> User:
    """
    Create a new user from storage provider auth.
    
    PRIVACY: No personal data (email, name, etc.) is stored.
    Only the anonymous user_id and provider info.
    """
    async with get_db_session() as session:
        user = User(
            id=user_id,
            primary_provider=provider,
            storage_user_id=storage_user_id,
            default_role=default_role,
            created_at=utc_now(),
            last_login=utc_now(),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_or_create_user(
    user_id: str,
    provider: str,
    storage_user_id: str,
    default_role: str = "tenant",
) -> tuple[User, bool]:
    """
    Get existing user or create new one.
    
    PRIVACY: No personal data (email, name, etc.) is stored or updated.
    
    Returns: (user, created: bool)
    """
    user = await get_user_by_id(user_id)
    if user:
        # Update last login only - no personal data
        async with get_db_session() as session:
            user.last_login = utc_now()
            session.add(user)
            await session.commit()
        return user, False
    
    user = await create_user(
        user_id=user_id,
        provider=provider,
        storage_user_id=storage_user_id,
        default_role=default_role,
    )
    return user, True


async def update_user_role(user_id: str, role: str) -> Optional[User]:
    """Update user's default role preference."""
    async with get_db_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.default_role = role
            user.updated_at = utc_now()
            await session.commit()
            await session.refresh(user)
        return user


# REMOVED: update_user_profile() - Semptify does not store personal data
# Any profile info the user wants lives in THEIR cloud storage, not our DB.


# =============================================================================
# Linked Providers
# =============================================================================

async def link_provider(
    user_id: str,
    provider: str,
    storage_user_id: str,
) -> LinkedProvider:
    """
    Link an additional storage provider to user's account.
    
    PRIVACY: No personal data (email, name, etc.) is stored.
    Only the anonymous provider identity.
    """
    async with get_db_session() as session:
        linked = LinkedProvider(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=provider,
            storage_user_id=storage_user_id,
            linked_at=utc_now(),
        )
        session.add(linked)
        await session.commit()
        await session.refresh(linked)
        return linked


async def get_linked_providers(user_id: str) -> list[LinkedProvider]:
    """Get all linked providers for a user."""
    async with get_db_session() as session:
        result = await session.execute(
            select(LinkedProvider)
            .where(LinkedProvider.user_id == user_id)
            .where(LinkedProvider.is_active == True)
        )
        return list(result.scalars().all())


async def unlink_provider(user_id: str, provider: str) -> bool:
    """Unlink a provider from user's account."""
    async with get_db_session() as session:
        result = await session.execute(
            select(LinkedProvider)
            .where(LinkedProvider.user_id == user_id)
            .where(LinkedProvider.provider == provider)
        )
        linked = result.scalar_one_or_none()
        if linked:
            linked.is_active = False
            await session.commit()
            return True
        return False


# =============================================================================
# User Lookup for Returning Users
# =============================================================================

async def get_user_auth_info(user_id: str) -> Optional[dict]:
    """
    Get the info needed to re-authenticate a returning user.
    
    PRIVACY: No personal data is returned - only provider and role info.
    
    Returns:
        {
            "user_id": "GU7x9kM2pQ",
            "primary_provider": "google_drive",
            "default_role": "tenant",
            "linked_providers": ["google_drive", "dropbox"]
        }
    """
    user = await get_user_by_id(user_id)
    if not user:
        return None
    
    linked = await get_linked_providers(user_id)
    
    return {
        "user_id": user.id,
        "primary_provider": user.primary_provider,
        "default_role": user.default_role,
        "linked_providers": [user.primary_provider] + [l.provider for l in linked],
    }
