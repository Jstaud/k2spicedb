"""
Schema generation module.
Provides deterministic conversion of KeycloakRealm data to a SpiceDB schema.
Used as a fallback when LLM-based generation is disabled.
"""

import logging
import re
from k2spicedb.keycloak_parser import KeycloakRealm

logger = logging.getLogger(__name__)


class SchemaGenerator:
    """Generates a SpiceDB schema from KeycloakRealm data without using an LLM."""

    @classmethod
    def sanitize_identifier(cls, name: str) -> str:
        """
        Converts a name into a valid SpiceDB identifier:
        - Replaces non-alphanumeric characters with underscores.
        - Prefixes with "_" if the name starts with a digit.
        """
        sanitized = re.sub(r'[^0-9a-zA-Z_]', '_', name)
        return f"_{sanitized}" if sanitized[0].isdigit() else sanitized

    @classmethod
    def generate_schema(cls, realm: KeycloakRealm) -> str:
        """
        Generates a SpiceDB schema definition from a KeycloakRealm.

        - Defines `user` and `group` objects.
        - Maps roles and permissions for realm and client roles.
        - Supports nested groups and composite roles.
        """
        schema_lines = []

        # Base user definition
        schema_lines.append("definition user {}")

        # Define groups with member relationships
        cls._add_group_definition(schema_lines, realm)

        # Define realm-level roles
        cls._add_realm_roles(schema_lines, realm)

        # Define client-specific roles
        cls._add_client_roles(schema_lines, realm)

        # Ensure realm name is included in the schema
        if not realm.realm_roles and not realm.client_roles and not realm.groups:
            schema_lines.insert(0, f"// Realm: {realm.name}")

        return "\n".join(schema_lines)

    @classmethod
    def _add_group_definition(cls, schema_lines: list, realm: KeycloakRealm):
        """Adds the SpiceDB group definition, supporting nested groups."""
        if not realm.groups:
            return

        group_def = [
            "definition group {",
            "    relation member: user"
        ]
        if any(group.subgroups for group in realm.groups):
            group_def.append("    relation parent: group")  # Support nested groups
        group_def.append("}")

        schema_lines.append("\n".join(group_def))

    @classmethod
    def _add_realm_roles(cls, schema_lines: list, realm: KeycloakRealm):
        """Adds SpiceDB object definitions for realm-level roles."""
        if not realm.realm_roles:
            return

        realm_def = ["definition realm {"]
        for role in realm.realm_roles:
            safe_role = cls.sanitize_identifier(role)
            realm_def.append(f"    relation {safe_role}: user")

        # Handle composite realm roles (permissions derived from multiple roles)
        for composite_role, parts in realm.composite_roles.items():
            if composite_role in realm.realm_roles:
                cls._add_composite_permissions(realm_def, composite_role, parts)

        realm_def.append("}")
        schema_lines.append("\n".join(realm_def))

    @classmethod
    def _add_client_roles(cls, schema_lines: list, realm: KeycloakRealm):
        """Adds SpiceDB object definitions for client roles."""
        for client, roles in realm.client_roles.items():
            safe_client = cls.sanitize_identifier(client)
            client_def = [f"definition {safe_client} {{"]

            for role in roles:
                safe_role = cls.sanitize_identifier(role)
                client_def.append(f"    relation {safe_role}: user")

            # Handle composite roles that only include roles from the same client
            for composite_role, parts in realm.composite_roles.items():
                if composite_role in roles:
                    cls._add_composite_permissions(client_def, composite_role, parts, roles)

            client_def.append("}")
            schema_lines.append("\n".join(client_def))

    @classmethod
    def _add_composite_permissions(cls, definition_lines: list, composite_role: str, parts: list, valid_roles=None):
        """
        Adds composite role permissions to the schema.
        - `valid_roles` is used to restrict composite roles to specific scopes (realm vs client).
        """
        safe_composite = cls.sanitize_identifier(composite_role)

        # Only include parts that are within the valid roles list (if provided)
        valid_parts = [cls.sanitize_identifier(p) for p in parts if not valid_roles or p in valid_roles]

        if valid_parts:
            definition_lines.append(f"    permission {safe_composite} = " + " + ".join(valid_parts))
        else:
            definition_lines.append(f"    // Composite role '{composite_role}' spans multiple scopes (not fully expanded)")
