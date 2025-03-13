"""
Keycloak Realm Export Parser.

This module provides functionality to parse a Keycloak realm export (JSON format)
and convert it into a structured Python representation for further processing.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict

logger = logging.getLogger(__name__)


@dataclass
class Group:
    """Represents a Keycloak Group, possibly with nested subgroups."""
    name: str
    subgroups: List["Group"] = field(default_factory=list)

    def all_subgroup_names(self) -> List[str]:
        """Recursively collects names of all subgroups."""
        return [subgroup.name for subgroup in self.subgroups] + \
               [name for subgroup in self.subgroups for name in subgroup.all_subgroup_names()]


@dataclass
class KeycloakRealm:
    """Structured representation of a Keycloak realm export."""
    name: str
    realm_roles: List[str] = field(default_factory=list)
    client_roles: Dict[str, List[str]] = field(default_factory=dict)
    groups: List[Group] = field(default_factory=list)
    composite_roles: Dict[str, List[str]] = field(default_factory=dict)


class KeycloakParser:
    """
    Parses Keycloak realm export files (JSON format).
    Extracts relevant data, including roles, groups, and composite role mappings.
    """

    def parse_file(self, file_path: str) -> KeycloakRealm:
        """
        Parses a Keycloak realm JSON export file and returns a structured representation.

        :param file_path: Path to the Keycloak JSON file.
        :return: KeycloakRealm object with parsed data.
        """
        logger.debug("Reading Keycloak realm export from file: %s", file_path)

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return self.parse_data(data)

    def parse_data(self, data: dict) -> KeycloakRealm:
        """
        Parses a Keycloak realm JSON object into a structured KeycloakRealm instance.

        :param data: Dictionary representing the Keycloak realm JSON.
        :return: KeycloakRealm object.
        """
        realm_name = data.get("realm") or data.get("id") or "UnnamedRealm"

        realm_roles = self._extract_realm_roles(data)
        client_roles = self._extract_client_roles(data)
        composite_roles = self._extract_composite_roles(data)
        groups = self._extract_groups(data)

        realm = KeycloakRealm(
            name=realm_name,
            realm_roles=realm_roles,
            client_roles=client_roles,
            groups=groups,
            composite_roles=composite_roles
        )

        logger.info("Parsed realm '%s': %d realm roles, %d client roles, %d top-level groups.",
                    realm.name,
                    len(realm.realm_roles),
                    sum(len(roles) for roles in realm.client_roles.values()),
                    len(realm.groups))

        if composite_roles:
            logger.info("Found %d composite role(s) in the realm export.", len(composite_roles))

        return realm

    def _extract_realm_roles(self, data: dict) -> List[str]:
        """Extracts and returns a list of realm-level roles."""
        return [role.get("name") for role in data.get("roles", {}).get("realm", []) if role.get("name")]

    def _extract_client_roles(self, data: dict) -> Dict[str, List[str]]:
        """Extracts and returns a dictionary of client-specific roles."""
        client_roles = {}
        for client, roles in data.get("roles", {}).get("client", {}).items():
            role_names = [role.get("name") for role in roles if role.get("name")]
            if role_names:
                client_roles[client] = role_names
        return client_roles

    def _extract_composite_roles(self, data: dict) -> Dict[str, List[str]]:
        """
        Extracts composite roles, mapping them to their component roles.
        Composite roles may include both realm and client roles.
        """
        composite_roles = {}
        for role in data.get("roles", {}).get("realm", []) + \
                sum(data.get("roles", {}).get("client", {}).values(), []):
            if role.get("composite") and role.get("composites"):
                components = self._extract_composite_components(role)
                if components:
                    composite_roles[role["name"]] = components
        return composite_roles

    def _extract_composite_components(self, role: dict) -> List[str]:
        """
        Extracts components of a composite role, combining realm and client roles.

        :param role: A Keycloak role dictionary.
        :return: List of component roles.
        """
        components = []
        composites = role.get("composites", {})

        components.extend(composites.get("realm", []))
        for client, roles in composites.get("client", {}).items():
            components.extend(f"{client}:{r}" for r in roles)

        return components

    def _extract_groups(self, data: dict) -> List[Group]:
        """Extracts and returns a list of Keycloak groups (including nested subgroups)."""
        return [self._parse_group(group) for group in data.get("groups", [])]

    def _parse_group(self, group_data: dict) -> Group:
        """
        Recursively parses a group (and its subgroups) from Keycloak data.

        :param group_data: Dictionary representing a group.
        :return: Group object with nested subgroups.
        """
        name = group_data.get("name", "")
        subgroups = [self._parse_group(sub) for sub in group_data.get("subGroups", [])]
        return Group(name=name, subgroups=subgroups)
