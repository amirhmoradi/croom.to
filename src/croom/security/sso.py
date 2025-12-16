"""
Single Sign-On (SSO) providers for Croom.

Supports SAML 2.0, OIDC/OAuth 2.0, and LDAP authentication.
"""

import base64
import hashlib
import json
import logging
import secrets
import time
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class SSOProvider(Enum):
    """Supported SSO providers."""
    SAML = "saml"
    OIDC = "oidc"
    LDAP = "ldap"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    GOOGLE = "google"


@dataclass
class SSOUser:
    """
    User information from SSO authentication.

    Attributes:
        user_id: Unique user identifier
        email: User email
        display_name: Display name
        given_name: First name
        family_name: Last name
        groups: Group memberships
        roles: Assigned roles
        attributes: Additional attributes
        provider: SSO provider used
        session_id: SSO session ID
    """
    user_id: str
    email: str
    display_name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    groups: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    provider: Optional[SSOProvider] = None
    session_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "given_name": self.given_name,
            "family_name": self.family_name,
            "groups": self.groups,
            "roles": self.roles,
            "attributes": self.attributes,
            "provider": self.provider.value if self.provider else None,
        }


class SSOAuthenticator(ABC):
    """Abstract base class for SSO authenticators."""

    @abstractmethod
    def get_login_url(self, state: Optional[str] = None) -> str:
        """Get the URL to redirect user for login."""
        pass

    @abstractmethod
    async def process_callback(self, data: Dict[str, Any]) -> Optional[SSOUser]:
        """Process the authentication callback."""
        pass

    @abstractmethod
    def get_logout_url(self, session_id: Optional[str] = None) -> Optional[str]:
        """Get the URL for logout."""
        pass


@dataclass
class SAMLConfig:
    """
    SAML 2.0 configuration.

    Attributes:
        entity_id: Service Provider entity ID
        sso_url: Identity Provider SSO URL
        slo_url: Identity Provider SLO URL
        certificate: IdP certificate for signature verification
        sp_cert: Service Provider certificate
        sp_key: Service Provider private key
        acs_url: Assertion Consumer Service URL
        name_id_format: NameID format
        signed_requests: Sign authentication requests
        want_signed_response: Require signed responses
        attribute_mapping: Attribute name mappings
    """
    entity_id: str
    sso_url: str
    slo_url: Optional[str] = None
    certificate: Optional[str] = None
    sp_cert: Optional[str] = None
    sp_key: Optional[str] = None
    acs_url: str = ""
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    signed_requests: bool = True
    want_signed_response: bool = True
    attribute_mapping: Dict[str, str] = field(default_factory=lambda: {
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "given_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "family_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "display_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "groups": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
    })


class SAMLAuthenticator(SSOAuthenticator):
    """
    SAML 2.0 authenticator.

    Provides Service Provider functionality for SAML authentication.
    """

    SAML_NS = {
        "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
        "ds": "http://www.w3.org/2000/09/xmldsig#",
    }

    def __init__(self, config: SAMLConfig):
        """
        Initialize SAML authenticator.

        Args:
            config: SAML configuration
        """
        self._config = config
        self._pending_requests: Dict[str, datetime] = {}

    def get_login_url(self, state: Optional[str] = None) -> str:
        """
        Generate SAML authentication request URL.

        Args:
            state: Optional state parameter

        Returns:
            Login redirect URL
        """
        # Generate request ID
        request_id = f"_{''.join(secrets.token_hex(16))}"
        self._pending_requests[request_id] = datetime.utcnow()

        # Build AuthnRequest
        request_xml = self._build_authn_request(request_id)

        # Encode and compress
        import zlib
        compressed = zlib.compress(request_xml.encode('utf-8'))[2:-4]  # Remove zlib header/checksum
        encoded = base64.b64encode(compressed).decode('ascii')

        # Build URL
        params = {
            "SAMLRequest": encoded,
        }
        if state:
            params["RelayState"] = state

        return f"{self._config.sso_url}?{urllib.parse.urlencode(params)}"

    def _build_authn_request(self, request_id: str) -> str:
        """Build SAML AuthnRequest XML."""
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{now}"
    Destination="{self._config.sso_url}"
    AssertionConsumerServiceURL="{self._config.acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self._config.entity_id}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="{self._config.name_id_format}"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""

    async def process_callback(self, data: Dict[str, Any]) -> Optional[SSOUser]:
        """
        Process SAML Response.

        Args:
            data: POST data from IdP

        Returns:
            Authenticated user or None
        """
        saml_response = data.get("SAMLResponse")
        if not saml_response:
            logger.error("No SAMLResponse in callback")
            return None

        try:
            # Decode response
            response_xml = base64.b64decode(saml_response).decode('utf-8')

            # Parse XML
            root = ET.fromstring(response_xml)

            # Verify response status
            status = root.find(".//samlp:StatusCode", self.SAML_NS)
            if status is not None:
                status_value = status.get("Value", "")
                if "Success" not in status_value:
                    logger.error(f"SAML authentication failed: {status_value}")
                    return None

            # Extract assertion
            assertion = root.find(".//saml:Assertion", self.SAML_NS)
            if assertion is None:
                logger.error("No assertion in SAML response")
                return None

            # Verify signature if required
            if self._config.want_signed_response:
                if not self._verify_signature(root):
                    logger.error("SAML signature verification failed")
                    return None

            # Extract user information
            return self._extract_user(assertion)

        except Exception as e:
            logger.error(f"SAML processing error: {e}")
            return None

    def _verify_signature(self, root: ET.Element) -> bool:
        """Verify XML signature."""
        # Full implementation would use xmlsec1 or signxml library
        # This is a placeholder - signature verification is critical for production
        logger.warning("SAML signature verification not fully implemented")

        # Check if signature exists
        signature = root.find(".//ds:Signature", self.SAML_NS)
        return signature is not None

    def _extract_user(self, assertion: ET.Element) -> Optional[SSOUser]:
        """Extract user information from SAML assertion."""
        try:
            # Get NameID
            name_id = assertion.find(".//saml:NameID", self.SAML_NS)
            user_id = name_id.text if name_id is not None else None

            if not user_id:
                return None

            # Get attributes
            attributes = {}
            attr_statement = assertion.find(".//saml:AttributeStatement", self.SAML_NS)

            if attr_statement is not None:
                for attr in attr_statement.findall("saml:Attribute", self.SAML_NS):
                    name = attr.get("Name", "")
                    values = [
                        v.text for v in attr.findall("saml:AttributeValue", self.SAML_NS)
                        if v.text
                    ]
                    if values:
                        attributes[name] = values[0] if len(values) == 1 else values

            # Map attributes
            mapping = self._config.attribute_mapping
            email = attributes.get(mapping.get("email", ""), user_id)
            given_name = attributes.get(mapping.get("given_name", ""))
            family_name = attributes.get(mapping.get("family_name", ""))
            display_name = attributes.get(mapping.get("display_name", ""))
            groups = attributes.get(mapping.get("groups", ""), [])

            if isinstance(groups, str):
                groups = [groups]

            return SSOUser(
                user_id=user_id,
                email=email if isinstance(email, str) else user_id,
                display_name=display_name if isinstance(display_name, str) else None,
                given_name=given_name if isinstance(given_name, str) else None,
                family_name=family_name if isinstance(family_name, str) else None,
                groups=groups,
                attributes=attributes,
                provider=SSOProvider.SAML,
            )

        except Exception as e:
            logger.error(f"SAML attribute extraction error: {e}")
            return None

    def get_logout_url(self, session_id: Optional[str] = None) -> Optional[str]:
        """Get SAML SLO URL."""
        if not self._config.slo_url:
            return None

        # Build LogoutRequest (simplified)
        return self._config.slo_url

    def get_metadata(self) -> str:
        """Generate SAML SP metadata XML."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{self._config.entity_id}">
    <SPSSODescriptor
        AuthnRequestsSigned="{'true' if self._config.signed_requests else 'false'}"
        WantAssertionsSigned="{'true' if self._config.want_signed_response else 'false'}"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <NameIDFormat>{self._config.name_id_format}</NameIDFormat>
        <AssertionConsumerService
            index="0"
            isDefault="true"
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{self._config.acs_url}"/>
    </SPSSODescriptor>
</EntityDescriptor>"""


@dataclass
class OIDCConfig:
    """
    OpenID Connect configuration.

    Attributes:
        client_id: OAuth client ID
        client_secret: OAuth client secret
        issuer: OIDC issuer URL
        authorization_endpoint: Authorization endpoint
        token_endpoint: Token endpoint
        userinfo_endpoint: UserInfo endpoint
        jwks_uri: JWKS URI for token verification
        redirect_uri: OAuth redirect URI
        scopes: OAuth scopes
        response_type: OAuth response type
    """
    client_id: str
    client_secret: str
    issuer: str
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    userinfo_endpoint: str = ""
    jwks_uri: str = ""
    redirect_uri: str = ""
    scopes: List[str] = field(default_factory=lambda: ["openid", "email", "profile"])
    response_type: str = "code"

    @classmethod
    async def from_discovery(cls, issuer: str, client_id: str, client_secret: str, redirect_uri: str) -> "OIDCConfig":
        """Create config from OIDC discovery."""
        import aiohttp

        discovery_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"

        async with aiohttp.ClientSession() as session:
            async with session.get(discovery_url) as response:
                if response.status != 200:
                    raise RuntimeError(f"OIDC discovery failed: {response.status}")
                config_data = await response.json()

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            issuer=issuer,
            authorization_endpoint=config_data.get("authorization_endpoint", ""),
            token_endpoint=config_data.get("token_endpoint", ""),
            userinfo_endpoint=config_data.get("userinfo_endpoint", ""),
            jwks_uri=config_data.get("jwks_uri", ""),
            redirect_uri=redirect_uri,
        )


class OIDCAuthenticator(SSOAuthenticator):
    """
    OpenID Connect authenticator.

    Supports standard OIDC providers and common enterprise IdPs.
    """

    def __init__(self, config: OIDCConfig):
        """
        Initialize OIDC authenticator.

        Args:
            config: OIDC configuration
        """
        self._config = config
        self._pending_states: Dict[str, datetime] = {}
        self._nonces: Dict[str, str] = {}

    def get_login_url(self, state: Optional[str] = None) -> str:
        """
        Generate OIDC authorization URL.

        Args:
            state: Optional state parameter

        Returns:
            Authorization URL
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        nonce = secrets.token_urlsafe(32)

        self._pending_states[state] = datetime.utcnow()
        self._nonces[state] = nonce

        params = {
            "client_id": self._config.client_id,
            "redirect_uri": self._config.redirect_uri,
            "response_type": self._config.response_type,
            "scope": " ".join(self._config.scopes),
            "state": state,
            "nonce": nonce,
        }

        return f"{self._config.authorization_endpoint}?{urllib.parse.urlencode(params)}"

    async def process_callback(self, data: Dict[str, Any]) -> Optional[SSOUser]:
        """
        Process OIDC callback.

        Args:
            data: Query parameters from callback

        Returns:
            Authenticated user or None
        """
        # Check for error
        if "error" in data:
            logger.error(f"OIDC error: {data.get('error_description', data['error'])}")
            return None

        # Verify state
        state = data.get("state")
        if not state or state not in self._pending_states:
            logger.error("Invalid or missing state parameter")
            return None

        # Check state age
        state_time = self._pending_states.pop(state)
        if datetime.utcnow() - state_time > timedelta(minutes=10):
            logger.error("State parameter expired")
            return None

        # Exchange code for tokens
        code = data.get("code")
        if not code:
            logger.error("No authorization code in callback")
            return None

        try:
            tokens = await self._exchange_code(code)
            if not tokens:
                return None

            # Get user info
            access_token = tokens.get("access_token")
            id_token = tokens.get("id_token")

            # Parse ID token claims
            claims = self._parse_jwt(id_token) if id_token else {}

            # Verify nonce
            expected_nonce = self._nonces.pop(state, None)
            if expected_nonce and claims.get("nonce") != expected_nonce:
                logger.error("Invalid nonce in ID token")
                return None

            # Get additional user info
            if access_token and self._config.userinfo_endpoint:
                userinfo = await self._get_userinfo(access_token)
                claims.update(userinfo)

            # Build user
            return SSOUser(
                user_id=claims.get("sub", ""),
                email=claims.get("email", ""),
                display_name=claims.get("name"),
                given_name=claims.get("given_name"),
                family_name=claims.get("family_name"),
                groups=claims.get("groups", []),
                attributes=claims,
                provider=SSOProvider.OIDC,
            )

        except Exception as e:
            logger.error(f"OIDC processing error: {e}")
            return None

    async def _exchange_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens."""
        import aiohttp

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._config.redirect_uri,
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._config.token_endpoint,
                data=data,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Token exchange failed: {error_text}")
                    return None
                return await response.json()

    async def _get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """Get user info from userinfo endpoint."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                self._config.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            ) as response:
                if response.status != 200:
                    return {}
                return await response.json()

    def _parse_jwt(self, token: str) -> Dict[str, Any]:
        """Parse JWT claims without verification (verification should be added)."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return {}

            # Decode payload
            payload = parts[1]
            # Add padding
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)

        except Exception as e:
            logger.error(f"JWT parse error: {e}")
            return {}

    def get_logout_url(self, session_id: Optional[str] = None) -> Optional[str]:
        """Get OIDC logout URL."""
        # Standard OIDC doesn't define logout
        # Some providers support end_session_endpoint
        return None


@dataclass
class LDAPConfig:
    """
    LDAP configuration.

    Attributes:
        server: LDAP server hostname
        port: LDAP port
        use_ssl: Use LDAPS
        use_tls: Use STARTTLS
        bind_dn: Bind DN for searches
        bind_password: Bind password
        base_dn: Base DN for searches
        user_search_filter: Filter for finding users
        user_id_attribute: Attribute containing user ID
        group_search_filter: Filter for finding groups
        group_member_attribute: Attribute containing group members
    """
    server: str
    port: int = 389
    use_ssl: bool = False
    use_tls: bool = True
    bind_dn: Optional[str] = None
    bind_password: Optional[str] = None
    base_dn: str = ""
    user_search_filter: str = "(uid={username})"
    user_id_attribute: str = "uid"
    email_attribute: str = "mail"
    display_name_attribute: str = "displayName"
    group_search_filter: str = "(member={user_dn})"
    group_member_attribute: str = "member"


class LDAPAuthenticator(SSOAuthenticator):
    """
    LDAP authenticator.

    Provides authentication against LDAP/Active Directory.
    """

    def __init__(self, config: LDAPConfig):
        """
        Initialize LDAP authenticator.

        Args:
            config: LDAP configuration
        """
        self._config = config
        self._ldap_available = self._check_ldap()

    def _check_ldap(self) -> bool:
        """Check if ldap3 library is available."""
        try:
            import ldap3
            return True
        except ImportError:
            logger.warning("ldap3 library not available")
            return False

    def get_login_url(self, state: Optional[str] = None) -> str:
        """LDAP doesn't use redirect-based login."""
        return ""

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> Optional[SSOUser]:
        """
        Authenticate user against LDAP.

        Args:
            username: Username
            password: Password

        Returns:
            Authenticated user or None
        """
        if not self._ldap_available:
            return None

        try:
            import ldap3
            from ldap3 import Server, Connection, ALL, SUBTREE

            # Connect to LDAP server
            server = Server(
                self._config.server,
                port=self._config.port,
                use_ssl=self._config.use_ssl,
                get_info=ALL,
            )

            # Bind with service account to search for user
            if self._config.bind_dn:
                search_conn = Connection(
                    server,
                    user=self._config.bind_dn,
                    password=self._config.bind_password,
                    auto_bind=True,
                )
            else:
                search_conn = Connection(server, auto_bind=True)

            if self._config.use_tls and not self._config.use_ssl:
                search_conn.start_tls()

            # Search for user
            search_filter = self._config.user_search_filter.format(username=username)
            search_conn.search(
                self._config.base_dn,
                search_filter,
                search_scope=SUBTREE,
                attributes=['*'],
            )

            if not search_conn.entries:
                logger.warning(f"User not found: {username}")
                return None

            user_entry = search_conn.entries[0]
            user_dn = user_entry.entry_dn
            search_conn.unbind()

            # Authenticate user
            user_conn = Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True,
            )

            if not user_conn.bound:
                logger.warning(f"Authentication failed for: {username}")
                return None

            # Get user attributes
            user_id = str(getattr(user_entry, self._config.user_id_attribute, username))
            email = str(getattr(user_entry, self._config.email_attribute, ""))
            display_name = str(getattr(user_entry, self._config.display_name_attribute, ""))

            # Get group memberships
            groups = await self._get_user_groups(server, user_dn)

            user_conn.unbind()

            return SSOUser(
                user_id=user_id,
                email=email,
                display_name=display_name,
                groups=groups,
                provider=SSOProvider.LDAP,
            )

        except Exception as e:
            logger.error(f"LDAP authentication error: {e}")
            return None

    async def _get_user_groups(self, server, user_dn: str) -> List[str]:
        """Get user's group memberships."""
        try:
            import ldap3
            from ldap3 import Connection, SUBTREE

            conn = Connection(
                server,
                user=self._config.bind_dn,
                password=self._config.bind_password,
                auto_bind=True,
            )

            search_filter = self._config.group_search_filter.format(user_dn=user_dn)
            conn.search(
                self._config.base_dn,
                search_filter,
                search_scope=SUBTREE,
                attributes=['cn'],
            )

            groups = [str(entry.cn) for entry in conn.entries]
            conn.unbind()

            return groups

        except Exception as e:
            logger.error(f"Group lookup error: {e}")
            return []

    async def process_callback(self, data: Dict[str, Any]) -> Optional[SSOUser]:
        """LDAP doesn't use callbacks - use authenticate() instead."""
        return None

    def get_logout_url(self, session_id: Optional[str] = None) -> Optional[str]:
        """LDAP doesn't have logout URL."""
        return None


class SSOService:
    """
    SSO service that manages multiple authenticators.

    Provides a unified interface for SSO authentication.
    """

    def __init__(self):
        """Initialize SSO service."""
        self._authenticators: Dict[str, SSOAuthenticator] = {}
        self._default_authenticator: Optional[str] = None
        self._group_role_mapping: Dict[str, List[str]] = {}

    def register_saml(
        self,
        name: str,
        config: SAMLConfig,
        default: bool = False,
    ) -> None:
        """Register a SAML authenticator."""
        self._authenticators[name] = SAMLAuthenticator(config)
        if default:
            self._default_authenticator = name
        logger.info(f"Registered SAML authenticator: {name}")

    def register_oidc(
        self,
        name: str,
        config: OIDCConfig,
        default: bool = False,
    ) -> None:
        """Register an OIDC authenticator."""
        self._authenticators[name] = OIDCAuthenticator(config)
        if default:
            self._default_authenticator = name
        logger.info(f"Registered OIDC authenticator: {name}")

    def register_ldap(
        self,
        name: str,
        config: LDAPConfig,
        default: bool = False,
    ) -> None:
        """Register an LDAP authenticator."""
        self._authenticators[name] = LDAPAuthenticator(config)
        if default:
            self._default_authenticator = name
        logger.info(f"Registered LDAP authenticator: {name}")

    def set_group_role_mapping(self, mapping: Dict[str, List[str]]) -> None:
        """
        Set group to role mapping.

        Args:
            mapping: Dict of group name to list of roles
        """
        self._group_role_mapping = mapping

    def get_login_url(
        self,
        authenticator: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Optional[str]:
        """Get login URL for an authenticator."""
        name = authenticator or self._default_authenticator

        if name not in self._authenticators:
            return None

        return self._authenticators[name].get_login_url(state)

    async def process_callback(
        self,
        authenticator: str,
        data: Dict[str, Any],
    ) -> Optional[SSOUser]:
        """
        Process authentication callback.

        Args:
            authenticator: Authenticator name
            data: Callback data

        Returns:
            Authenticated user or None
        """
        if authenticator not in self._authenticators:
            return None

        user = await self._authenticators[authenticator].process_callback(data)

        if user:
            # Apply group-role mapping
            user.roles = self._map_groups_to_roles(user.groups)

        return user

    async def authenticate_ldap(
        self,
        username: str,
        password: str,
        authenticator: Optional[str] = None,
    ) -> Optional[SSOUser]:
        """
        Authenticate against LDAP.

        Args:
            username: Username
            password: Password
            authenticator: LDAP authenticator name

        Returns:
            Authenticated user or None
        """
        name = authenticator or self._default_authenticator

        if name not in self._authenticators:
            return None

        auth = self._authenticators[name]
        if not isinstance(auth, LDAPAuthenticator):
            return None

        user = await auth.authenticate(username, password)

        if user:
            user.roles = self._map_groups_to_roles(user.groups)

        return user

    def _map_groups_to_roles(self, groups: List[str]) -> List[str]:
        """Map group memberships to roles."""
        roles = set()

        for group in groups:
            if group in self._group_role_mapping:
                roles.update(self._group_role_mapping[group])

        return list(roles)

    def list_authenticators(self) -> List[str]:
        """List registered authenticators."""
        return list(self._authenticators.keys())

    def get_logout_url(
        self,
        authenticator: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """Get logout URL for an authenticator."""
        name = authenticator or self._default_authenticator

        if name not in self._authenticators:
            return None

        return self._authenticators[name].get_logout_url(session_id)
