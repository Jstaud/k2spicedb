"""
Schema generation module.
Provides deterministic conversion of KeycloakRealm data to a SpiceDB schema (used for fallback or optional non-LLM mode).
"""
import logging
import re

from k2spicedb.keycloak_parser import KeycloakRealm

logger = logging.getLogger(__name__)

class SchemaGenerator:
    """Generates a SpiceDB schema from KeycloakRealm data without using LLM."""
    
    @classmethod
    def sanitize_identifier(cls, name: str) -> str:
        """
        Sanitize a string to be a valid identifier in SpiceDB schema.
        Non-alphanumeric characters are replaced with '_', and leading digits are prefixed with '_'.
        """
        sanitized = re.sub(r'[^0-9a-zA-Z_]', '_', name)
        if sanitized and sanitized[0].isdigit():
            sanitized = "_" + sanitized
        return sanitized

    @classmethod
    def generate_schema(cls, realm: KeycloakRealm) -> str:
        """
        Generate a SpiceDB schema definition (as text) from the given KeycloakRealm.
        This provides a basic mapping of users, groups, and roles to SpiceDB object definitions and relations.
        """
        lines = []
        # Base user object definition
        lines.append("definition user {}")
        # Group object definition (with membership and optional parent relation if nested groups exist)
        if realm.groups:
            group_def = "definition group {\n    relation member: user"
            if any(group.subgroups for group in realm.groups):
                group_def += "\n    relation parent: group"
            group_def += "\n}"
            lines.append(group_def)
        # Realm object definition for realm-level roles (if any)
        if realm.realm_roles:
            realm_def_lines = ["definition realm {"]
            for role_name in realm.realm_roles:
                safe_role = cls.sanitize_identifier(role_name)
                realm_def_lines.append(f"    relation {safe_role}: user")
            # Define permissions for composite realm roles (union of base roles) if applicable
            for comp, parts in realm.composite_roles.items():
                if comp in realm.realm_roles:
                    # Only handle if all parts are realm roles (ignore client roles in composite for schema)
                    if all(":" not in p for p in parts):
                        safe_comp = cls.sanitize_identifier(comp)
                        part_relations = [cls.sanitize_identifier(p) for p in parts]
                        if part_relations:
                            realm_def_lines.append(f"    permission {safe_comp} = " + " + ".join(part_relations))
                    else:
                        realm_def_lines.append(f"    // Composite role '{comp}' spans multiple scopes (not fully expanded)")
            realm_def_lines.append("}")
            lines.append("\n".join(realm_def_lines))
        # Object definitions for each client with roles
        for client, roles in realm.client_roles.items():
            safe_obj = cls.sanitize_identifier(client)
            client_def_lines = [f"definition {safe_obj} {{"]  # open brace
            for role_name in roles:
                safe_role = cls.sanitize_identifier(role_name)
                client_def_lines.append(f"    relation {safe_role}: user")
            # Permissions for composite client roles that include only roles of this same client
            for comp, parts in realm.composite_roles.items():
                if comp in roles:
                    if all(((":" not in p) and (p in roles)) for p in parts):
                        safe_comp = cls.sanitize_identifier(comp)
                        part_relations = [cls.sanitize_identifier(p) for p in parts if ":" not in p]
                        if part_relations:
                            client_def_lines.append(f"    permission {safe_comp} = " + " + ".join(part_relations))
                    else:
                        client_def_lines.append(f"    // Composite role '{comp}' spans multiple scopes (not fully expanded)")
            client_def_lines.append("}")
            lines.append("\n".join(client_def_lines))
        # Combine all lines into final schema text
        schema_text = "\n".join(lines)
        return schema_text
