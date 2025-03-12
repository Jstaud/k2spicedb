import io
import json
import unittest

from k2spicedb.keycloak_parser import KeycloakParser, KeycloakRealm, Group

# Disable logging while testing to keep output clean
import logging
logging.disable(logging.CRITICAL)

class TestKeycloakParser(unittest.TestCase):
    def setUp(self):
        self.parser = KeycloakParser()

    def test_parse_basic_realm(self):
        # Construct a minimal realm JSON structure
        realm_data = {
            "realm": "TestRealm",
            "roles": {
                "realm": [
                    {"name": "admin", "composite": False},
                    {"name": "user", "composite": False},
                    {"name": "composite_role", "composite": True, 
                     "composites": {"realm": ["admin"], "client": {"myapp": ["app_viewer"]}}}
                ],
                "client": {
                    "myapp": [
                        {"name": "app_admin", "composite": False},
                        {"name": "app_viewer", "composite": False}
                    ]
                }
            },
            "groups": [
                {"name": "group1", "subGroups": [
                    {"name": "subgroup1", "subGroups": []}
                ]},
                {"name": "group2", "subGroups": []}
            ]
        }
        # Use parse_data directly with the dictionary
        realm = self.parser.parse_data(realm_data)
        # Assertions on parsed structure
        self.assertIsInstance(realm, KeycloakRealm)
        self.assertEqual(realm.name, "TestRealm")
        # Realm roles should include 'admin', 'user', 'composite_role'
        self.assertIn("admin", realm.realm_roles)
        self.assertIn("user", realm.realm_roles)
        self.assertIn("composite_role", realm.realm_roles)
        # Client roles for 'myapp'
        self.assertIn("myapp", realm.client_roles)
        self.assertListEqual(sorted(realm.client_roles["myapp"]), ["app_admin", "app_viewer"])
        # Groups structure
        self.assertEqual(len(realm.groups), 2)
        top_names = sorted([g.name for g in realm.groups])
        self.assertListEqual(top_names, ["group1", "group2"])
        # Nested subgroup
        group1 = next(g for g in realm.groups if g.name == "group1")
        self.assertEqual(len(group1.subgroups), 1)
        self.assertEqual(group1.subgroups[0].name, "subgroup1")
        # Composite roles mapping
        # 'composite_role' should include 'admin' (realm role) and 'myapp:app_viewer' (client role reference)
        self.assertIn("composite_role", realm.composite_roles)
        comp_parts = realm.composite_roles["composite_role"]
        self.assertIn("admin", comp_parts)
        self.assertIn("myapp:app_viewer", comp_parts)
