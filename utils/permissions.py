import os

OWNER_ID = int(os.getenv("OWNER_ID", "0"))
OVERSEER_ROLE_ID = int(os.getenv("OVERSEER_ROLE_ID", "0"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0"))
DEV_ROLE_ID = int(os.getenv("DEV_ROLE_ID", "0"))


def has_permission(member):
    """
    Returns True if user can manage league systems
    """

    # OWNER override
    if member.id == OWNER_ID:
        return True

    role_ids = [role.id for role in member.roles]

    if OVERSEER_ROLE_ID in role_ids:
        return True
    if ADMIN_ROLE_ID in role_ids:
        return True
    if DEV_ROLE_ID in role_ids:
        return True

    return False


def is_owner(member):
    return member.id == OWNER_ID