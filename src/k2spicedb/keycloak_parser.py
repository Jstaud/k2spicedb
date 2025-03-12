"""
Keycloak realm export parser module.
Provides functionality to parse a Keycloak realm export (JSON format) and convert it 
into a structured Python representation for further processing.
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
    subgroups: List['Group'] = field(default_factory=list)

    def all_subgroup_names(self) -> List[str]:
        """Recursively gather names of all nested subgroups (for informational use)."""
        names: List[str] = []
        for subgroup in self.subgroups:
            names.append(subgroup.name)
            names.extend(subgroup.all_subgroup_names())
        return names

@dataclass
class KeycloakRealm:
    """Data structure for relevant content of a Keycloak realm export."""
    name: str
    realm_roles: List[str] = field(default_factory=list)
    client_roles: Dict[str, List[str]] = field(default_factory=dict)
    groups: List[Group] = field(default_factory=list)
    composite_roles: Dict[str, List[str]] = field(default_factory=dict)

class KeycloakParser:
    """
    Parser for Keycloak realm export files.
    Capable of reading a Keycloak realm JSON and extracting roles, groups, etc.
    """
    def parse_file(self, file_path: str) -> KeycloakRealm:
        """
        Parse a Keycloak realm export JSON file and return a KeycloakRealm object.
        :param file_path: Path to the Keycloak realm JSON file.
        :return: KeycloakRealm object with parsed data.
        """
        logger.debug(f"Reading Keycloak realm export from file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self.parse_data(data)

    def parse_data(self, data: dict) -> KeycloakRealm:
        """
        Parse a Keycloak realm export from a dictionary (already loaded from JSON).
        :param data: Dictionary representing the Keycloak realm JSON.
        :return: KeycloakRealm object with parsed data.
        """
        realm_name = data.get("realm") or data.get("id") or "UnnamedRealm"
        realm_roles: List[str] = []
        client_roles: Dict[str, List[str]] = {}
        composite_roles: Dict[str, List[str]] = {}
        # Parse realm-level roles
        roles_data = data.get("roles", {})
        for role in roles_data.get("realm", []):
            name = role.get("name")
            if not name:
                continue
            realm_roles.append(name)
            # If role is composite, record its components (role names, possibly with client prefix)
            if role.get("composite") and role.get("composites"):
                comp_list: List[str] = []
                comps = role.get("composites", {})
                for r in comps.get("realm", []):
                    comp_list.append(str(r))
                for client, roles_list in comps.get("client", {}).items():
                    for r in roles_list:
                        comp_list.append(f"{client}:{r}")
                if comp_list:
                    composite_roles[name] = comp_list
        # Parse client roles
        for client, roles_list in roles_data.get("client", {}).items():
            client_role_names: List[str] = []
            for role in roles_list:
                name = role.get("name")
                if not name:
                    continue
                client_role_names.append(name)
                if role.get("composite") and role.get("composites"):
                    comp_list: List[str] = []
                    comps = role.get("composites", {})
                    for r in comps.get("realm", []):
                        comp_list.append(str(r))
                    for client2, roles2 in comps.get("client", {}).items():
                        for r2 in roles2:
                            comp_list.append(f"{client2}:{r2}")
                    if comp_list:
                        composite_roles[name] = comp_list
            if client_role_names:
                client_roles[client] = client_role_names
        # Parse groups (including nested subgroups)
        groups: List[Group] = []
        for g in data.get("groups", []):
            group_obj = self._parse_group(g)
            groups.append(group_obj)
        realm = KeycloakRealm(
            name=realm_name,
            realm_roles=realm_roles,
            client_roles=client_roles,
            groups=groups,
            composite_roles=composite_roles
        )
        logger.info(f"Parsed realm '{realm.name}': "
                    f"{len(realm.realm_roles)} realm roles, "
                    f"{sum(len(v) for v in realm.client_roles.values())} client roles, "
                    f"{len(realm.groups)} top-level groups.")
        if composite_roles:
            logger.info(f"Found {len(composite_roles)} composite role(s) in the realm export.")
        return realm

    def _parse_group(self, group_data: dict) -> Group:
        """
        Recursively parse a group (and its subgroups) from Keycloak data.
        :param group_data: Dictionary representing a group.
        :return: Group object with nested subgroups.
        """
        name = group_data.get("name", "")
        group_obj = Group(name=name)
        subgroups_data = group_data.get("subGroups") or group_data.get("subgroups") or []
        for sub in subgroups_data:
            subgroup_obj = self._parse_group(sub)
            group_obj.subgroups.append(subgroup_obj)
        return group_obj
