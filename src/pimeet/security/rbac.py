"""
Role-Based Access Control (RBAC) for PiMeet.

Provides fine-grained access control with roles and permissions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable

logger = logging.getLogger(__name__)


class Permission(Enum):
    """System permissions."""
    # Device permissions
    DEVICE_VIEW = "device:view"
    DEVICE_CREATE = "device:create"
    DEVICE_EDIT = "device:edit"
    DEVICE_DELETE = "device:delete"
    DEVICE_REBOOT = "device:reboot"
    DEVICE_LOGS = "device:logs"
    DEVICE_SHELL = "device:shell"

    # Credential permissions
    CREDENTIAL_VIEW = "credential:view"
    CREDENTIAL_CREATE = "credential:create"
    CREDENTIAL_EDIT = "credential:edit"
    CREDENTIAL_DELETE = "credential:delete"
    CREDENTIAL_ROTATE = "credential:rotate"

    # User permissions
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_EDIT = "user:edit"
    USER_DELETE = "user:delete"
    USER_RESET_PASSWORD = "user:reset_password"
    USER_MANAGE_MFA = "user:manage_mfa"

    # Role permissions
    ROLE_VIEW = "role:view"
    ROLE_CREATE = "role:create"
    ROLE_EDIT = "role:edit"
    ROLE_DELETE = "role:delete"
    ROLE_ASSIGN = "role:assign"

    # Audit permissions
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"

    # Settings permissions
    SETTINGS_VIEW = "settings:view"
    SETTINGS_EDIT = "settings:edit"

    # Meeting permissions
    MEETING_VIEW = "meeting:view"
    MEETING_JOIN = "meeting:join"
    MEETING_END = "meeting:end"

    # Analytics permissions
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"

    # API permissions
    API_ACCESS = "api:access"
    API_ADMIN = "api:admin"

    # System permissions
    SYSTEM_ADMIN = "system:admin"


class ResourceType(Enum):
    """Resource types for scoped permissions."""
    GLOBAL = "global"
    DEVICE = "device"
    DEVICE_GROUP = "device_group"
    LOCATION = "location"
    USER = "user"
    ROLE = "role"


@dataclass
class Role:
    """
    A user role with permissions.

    Attributes:
        role_id: Unique identifier
        name: Human-readable name
        description: Role description
        permissions: Set of permissions
        is_system: Whether this is a built-in system role
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    role_id: str
    name: str
    description: str
    permissions: Set[Permission] = field(default_factory=set)
    is_system: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has a permission."""
        return permission in self.permissions

    def add_permission(self, permission: Permission) -> None:
        """Add a permission to the role."""
        self.permissions.add(permission)
        self.updated_at = datetime.utcnow()

    def remove_permission(self, permission: Permission) -> None:
        """Remove a permission from the role."""
        self.permissions.discard(permission)
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "permissions": [p.value for p in self.permissions],
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Role":
        """Deserialize from dictionary."""
        return cls(
            role_id=data["role_id"],
            name=data["name"],
            description=data["description"],
            permissions={Permission(p) for p in data.get("permissions", [])},
            is_system=data.get("is_system", False),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
        )


@dataclass
class ResourceScope:
    """
    Scoped access to a resource.

    Allows restricting permissions to specific resources.
    """
    resource_type: ResourceType
    resource_id: Optional[str] = None  # None = all resources of this type
    permissions: Set[Permission] = field(default_factory=set)

    def matches(self, resource_type: ResourceType, resource_id: Optional[str]) -> bool:
        """Check if scope matches a resource."""
        if self.resource_type != resource_type:
            return False
        if self.resource_id is None:  # Scope applies to all
            return True
        return self.resource_id == resource_id


@dataclass
class AccessDecision:
    """
    Result of an access control decision.

    Attributes:
        allowed: Whether access is allowed
        reason: Explanation of the decision
        matched_role: Role that granted access (if allowed)
        matched_scope: Scope that granted access (if allowed)
    """
    allowed: bool
    reason: str
    matched_role: Optional[str] = None
    matched_scope: Optional[ResourceScope] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "matched_role": self.matched_role,
        }


# Default system roles
DEFAULT_ROLES = {
    "super_admin": Role(
        role_id="super_admin",
        name="Super Administrator",
        description="Full system access",
        permissions=set(Permission),  # All permissions
        is_system=True,
    ),
    "it_admin": Role(
        role_id="it_admin",
        name="IT Administrator",
        description="Device and configuration management",
        permissions={
            Permission.DEVICE_VIEW,
            Permission.DEVICE_CREATE,
            Permission.DEVICE_EDIT,
            Permission.DEVICE_DELETE,
            Permission.DEVICE_REBOOT,
            Permission.DEVICE_LOGS,
            Permission.CREDENTIAL_VIEW,
            Permission.CREDENTIAL_CREATE,
            Permission.CREDENTIAL_EDIT,
            Permission.CREDENTIAL_ROTATE,
            Permission.AUDIT_VIEW,
            Permission.SETTINGS_VIEW,
            Permission.ANALYTICS_VIEW,
            Permission.ANALYTICS_EXPORT,
            Permission.API_ACCESS,
        },
        is_system=True,
    ),
    "site_admin": Role(
        role_id="site_admin",
        name="Site Administrator",
        description="Manage devices at specific location",
        permissions={
            Permission.DEVICE_VIEW,
            Permission.DEVICE_EDIT,
            Permission.DEVICE_REBOOT,
            Permission.DEVICE_LOGS,
            Permission.CREDENTIAL_VIEW,
            Permission.CREDENTIAL_EDIT,
            Permission.AUDIT_VIEW,
            Permission.ANALYTICS_VIEW,
        },
        is_system=True,
    ),
    "operator": Role(
        role_id="operator",
        name="Operator",
        description="View and basic troubleshooting",
        permissions={
            Permission.DEVICE_VIEW,
            Permission.DEVICE_REBOOT,
            Permission.DEVICE_LOGS,
            Permission.MEETING_VIEW,
            Permission.MEETING_JOIN,
            Permission.MEETING_END,
        },
        is_system=True,
    ),
    "viewer": Role(
        role_id="viewer",
        name="Viewer",
        description="Read-only access",
        permissions={
            Permission.DEVICE_VIEW,
            Permission.MEETING_VIEW,
            Permission.ANALYTICS_VIEW,
        },
        is_system=True,
    ),
    "api_service": Role(
        role_id="api_service",
        name="API Service Account",
        description="Programmatic API access",
        permissions={
            Permission.API_ACCESS,
            Permission.DEVICE_VIEW,
            Permission.DEVICE_EDIT,
            Permission.MEETING_VIEW,
        },
        is_system=True,
    ),
}


class RBACService:
    """
    Role-Based Access Control service.

    Manages roles, permissions, and access decisions.
    """

    def __init__(self):
        """Initialize RBAC service."""
        # Role storage
        self._roles: Dict[str, Role] = dict(DEFAULT_ROLES)

        # User role assignments: user_id -> list of (role_id, optional scope)
        self._user_roles: Dict[str, List[tuple]] = {}

        # Access decision callbacks
        self._on_access_decision: Optional[Callable[[str, Permission, AccessDecision], None]] = None

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get a role by ID."""
        return self._roles.get(role_id)

    def list_roles(self) -> List[Role]:
        """List all roles."""
        return list(self._roles.values())

    def create_role(
        self,
        role_id: str,
        name: str,
        description: str,
        permissions: Optional[Set[Permission]] = None,
    ) -> Role:
        """
        Create a new role.

        Args:
            role_id: Unique identifier
            name: Human-readable name
            description: Role description
            permissions: Initial permissions

        Returns:
            Created role

        Raises:
            ValueError: If role_id already exists
        """
        if role_id in self._roles:
            raise ValueError(f"Role already exists: {role_id}")

        role = Role(
            role_id=role_id,
            name=name,
            description=description,
            permissions=permissions or set(),
        )

        self._roles[role_id] = role
        logger.info(f"Created role: {name}")

        return role

    def update_role(
        self,
        role_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[Set[Permission]] = None,
    ) -> bool:
        """
        Update a role.

        Args:
            role_id: Role to update
            name: New name
            description: New description
            permissions: New permissions (replaces existing)

        Returns:
            True if updated successfully
        """
        role = self._roles.get(role_id)

        if role is None:
            return False

        if role.is_system:
            logger.warning(f"Cannot modify system role: {role_id}")
            return False

        if name:
            role.name = name
        if description:
            role.description = description
        if permissions is not None:
            role.permissions = permissions

        role.updated_at = datetime.utcnow()
        logger.info(f"Updated role: {role.name}")

        return True

    def delete_role(self, role_id: str) -> bool:
        """
        Delete a role.

        Args:
            role_id: Role to delete

        Returns:
            True if deleted successfully
        """
        role = self._roles.get(role_id)

        if role is None:
            return False

        if role.is_system:
            logger.warning(f"Cannot delete system role: {role_id}")
            return False

        del self._roles[role_id]

        # Remove role assignments
        for user_id in self._user_roles:
            self._user_roles[user_id] = [
                (r, s) for r, s in self._user_roles[user_id]
                if r != role_id
            ]

        logger.info(f"Deleted role: {role.name}")
        return True

    def assign_role(
        self,
        user_id: str,
        role_id: str,
        scope: Optional[ResourceScope] = None,
    ) -> bool:
        """
        Assign a role to a user.

        Args:
            user_id: User to assign role to
            role_id: Role to assign
            scope: Optional scope restriction

        Returns:
            True if assigned successfully
        """
        if role_id not in self._roles:
            logger.warning(f"Role not found: {role_id}")
            return False

        if user_id not in self._user_roles:
            self._user_roles[user_id] = []

        # Check if already assigned
        for existing_role, existing_scope in self._user_roles[user_id]:
            if existing_role == role_id:
                if scope == existing_scope:
                    return True  # Already assigned

        self._user_roles[user_id].append((role_id, scope))
        logger.info(f"Assigned role {role_id} to user {user_id}")

        return True

    def revoke_role(
        self,
        user_id: str,
        role_id: str,
        scope: Optional[ResourceScope] = None,
    ) -> bool:
        """
        Revoke a role from a user.

        Args:
            user_id: User to revoke role from
            role_id: Role to revoke
            scope: Scope to revoke (None = all)

        Returns:
            True if revoked successfully
        """
        if user_id not in self._user_roles:
            return False

        original_count = len(self._user_roles[user_id])

        if scope is None:
            # Revoke all assignments of this role
            self._user_roles[user_id] = [
                (r, s) for r, s in self._user_roles[user_id]
                if r != role_id
            ]
        else:
            # Revoke specific scope
            self._user_roles[user_id] = [
                (r, s) for r, s in self._user_roles[user_id]
                if not (r == role_id and s == scope)
            ]

        revoked = len(self._user_roles[user_id]) < original_count

        if revoked:
            logger.info(f"Revoked role {role_id} from user {user_id}")

        return revoked

    def get_user_roles(self, user_id: str) -> List[Role]:
        """Get all roles assigned to a user."""
        role_ids = {r for r, _ in self._user_roles.get(user_id, [])}
        return [self._roles[r] for r in role_ids if r in self._roles]

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user."""
        permissions = set()

        for role_id, _ in self._user_roles.get(user_id, []):
            role = self._roles.get(role_id)
            if role:
                permissions.update(role.permissions)

        return permissions

    def check_permission(
        self,
        user_id: str,
        permission: Permission,
        resource_type: Optional[ResourceType] = None,
        resource_id: Optional[str] = None,
    ) -> AccessDecision:
        """
        Check if a user has a permission.

        Args:
            user_id: User to check
            permission: Permission required
            resource_type: Optional resource type
            resource_id: Optional specific resource

        Returns:
            AccessDecision with result
        """
        # Super admin always has access
        if self._has_role(user_id, "super_admin"):
            return AccessDecision(
                allowed=True,
                reason="Super administrator access",
                matched_role="super_admin",
            )

        # Check each role assignment
        for role_id, scope in self._user_roles.get(user_id, []):
            role = self._roles.get(role_id)

            if role is None:
                continue

            if permission not in role.permissions:
                continue

            # Check scope if specified
            if scope is not None and resource_type is not None:
                if not scope.matches(resource_type, resource_id):
                    continue

                # For scoped roles, check scoped permissions
                if scope.permissions and permission not in scope.permissions:
                    continue

            decision = AccessDecision(
                allowed=True,
                reason=f"Permission granted by role: {role.name}",
                matched_role=role_id,
                matched_scope=scope,
            )

            # Callback for audit
            if self._on_access_decision:
                self._on_access_decision(user_id, permission, decision)

            return decision

        # No matching permission found
        decision = AccessDecision(
            allowed=False,
            reason="Permission denied: insufficient privileges",
        )

        if self._on_access_decision:
            self._on_access_decision(user_id, permission, decision)

        return decision

    def require_permission(
        self,
        user_id: str,
        permission: Permission,
        resource_type: Optional[ResourceType] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """
        Require a permission, raising exception if denied.

        Args:
            user_id: User to check
            permission: Permission required
            resource_type: Optional resource type
            resource_id: Optional specific resource

        Raises:
            PermissionError: If access is denied
        """
        decision = self.check_permission(user_id, permission, resource_type, resource_id)

        if not decision.allowed:
            raise PermissionError(decision.reason)

    def _has_role(self, user_id: str, role_id: str) -> bool:
        """Check if user has a specific role."""
        return any(
            r == role_id
            for r, _ in self._user_roles.get(user_id, [])
        )

    def on_access_decision(
        self,
        callback: Callable[[str, Permission, AccessDecision], None],
    ) -> None:
        """Register callback for access decisions."""
        self._on_access_decision = callback

    def export_config(self) -> Dict[str, Any]:
        """Export RBAC configuration."""
        return {
            "roles": [
                role.to_dict()
                for role in self._roles.values()
                if not role.is_system
            ],
            "assignments": {
                user_id: [
                    {
                        "role_id": role_id,
                        "scope": {
                            "resource_type": scope.resource_type.value,
                            "resource_id": scope.resource_id,
                            "permissions": [p.value for p in scope.permissions],
                        } if scope else None,
                    }
                    for role_id, scope in assignments
                ]
                for user_id, assignments in self._user_roles.items()
            },
        }

    def import_config(self, config: Dict[str, Any]) -> None:
        """Import RBAC configuration."""
        # Import roles
        for role_data in config.get("roles", []):
            role = Role.from_dict(role_data)
            if role.role_id not in self._roles:
                self._roles[role.role_id] = role

        # Import assignments
        for user_id, assignments in config.get("assignments", {}).items():
            self._user_roles[user_id] = []

            for assignment in assignments:
                role_id = assignment["role_id"]
                scope_data = assignment.get("scope")

                scope = None
                if scope_data:
                    scope = ResourceScope(
                        resource_type=ResourceType(scope_data["resource_type"]),
                        resource_id=scope_data.get("resource_id"),
                        permissions={Permission(p) for p in scope_data.get("permissions", [])},
                    )

                self._user_roles[user_id].append((role_id, scope))


def create_rbac_service() -> RBACService:
    """Create an RBAC service with default configuration."""
    return RBACService()
