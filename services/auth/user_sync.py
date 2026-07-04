import logging
import uuid
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


def get_or_create_user(identity: dict) -> tuple:
    """
    Retrieves or creates a local Django User corresponding to the normalized Supabase identity.
    Matches are performed by:
      1. supabase_user_id
      2. email (with a fallback update to link the supabase_user_id)
    Returns:
      (User, bool) - The User instance and a boolean flag indicating if the model was created.
    """
    supabase_id = identity.get("supabase_user_id")
    email = identity.get("email")

    if not supabase_id:
        raise ValueError("User lookup/creation requires 'supabase_user_id'.")

    # 1. Match by Supabase User ID first
    user = User.objects.filter(supabase_user_id=supabase_id).first()
    if user:
        logger.debug(f"Matched existing user by supabase_user_id: {supabase_id}")
        return user, False

    # 2. Fallback: Match by email if vorhanden
    if email:
        user = User.objects.filter(email=email).first()
        if user:
            logger.info(f"Matched existing user by email: {email}. Linking supabase_user_id: {supabase_id}")
            user.supabase_user_id = supabase_id
            user.save(update_fields=["supabase_user_id"])
            return user, False

    # 3. Create a new User
    username = None
    if email:
        local_part = email.split("@")[0]
        # Allow only alphanumeric and common separator characters for safe Django username
        clean_local = "".join(c for c in local_part if c.isalnum() or c in ".-_")[:150]
        
        # Check uniqueness of username
        if not User.objects.filter(username=clean_local).exists():
            username = clean_local
            
    if not username:
        # Create unique username using UUID to guarantee constraint satisfaction
        username = f"user_{uuid.uuid4().hex[:15]}"

    logger.info(f"Creating new Django User with username: {username} and email: {email}")
    user = User.objects.create(
        username=username,
        email=email or "",
        supabase_user_id=supabase_id,
        provider=identity.get("provider", ""),
        role=identity.get("role", ""),
        email_verified=identity.get("email_verified", False)
    )
    user.set_unusable_password()
    user.save()
    
    return user, True


def update_existing_user(user, identity: dict) -> bool:
    """
    Idempotently updates mutable attributes of an existing Django User model mapping
    to the Supabase Auth specs.
    Returns:
      True if the model was modified and saved, False if no changes were needed.
    """
    updated = False
    fields_to_update = []

    # Map inputs, treating None as empty string for normalization
    email_val = identity.get("email") or ""
    provider_val = identity.get("provider") or ""
    role_val = identity.get("role") or ""
    verified_val = bool(identity.get("email_verified", False))

    if user.email != email_val:
        user.email = email_val
        fields_to_update.append("email")
        updated = True

    if user.provider != provider_val:
        user.provider = provider_val
        fields_to_update.append("provider")
        updated = True

    if user.role != role_val:
        user.role = role_val
        fields_to_update.append("role")
        updated = True

    if user.email_verified != verified_val:
        user.email_verified = verified_val
        fields_to_update.append("email_verified")
        updated = True

    if updated:
        logger.info(f"Updating user fields: {fields_to_update} on user: {user.username}")
        user.save(update_fields=fields_to_update)

    return updated


def synchronize_user(identity: dict):
    """
    Coordinates User retrieval/creation and idempotency synchronization.
    Returns the synchronized Django User instance.
    """
    user, created = get_or_create_user(identity)
    if not created:
        update_existing_user(user, identity)
    return user
