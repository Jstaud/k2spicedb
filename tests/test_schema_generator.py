import unittest
from k2spicedb.keycloak_parser import KeycloakRealm, Group
from k2spicedb.schema_generator import SchemaGenerator

# Disable logging
import logging
logging.disable(logging.CRITICAL)

class TestSchemaGenerator(unittest.TestCase):
    def test_generate_schema_basic(self):
        
        # Create a realm with one realm role, one client role, and groups
        group = Group(name="team1", subgroups=[Group(name="team1_sub")])
        
        realm = KeycloakRealm(
            name="TestRealm",
            realm_roles=["admin"], 
            client_roles={"app": ["read"]},
            groups=[group],
            composite_roles={}  # no composite in this test
        )
        schema = SchemaGenerator.generate_schema(realm)
        
        # Basic components should be present
        self.assertIn("definition user {}", schema)
        
        # Group definition with member relation
        self.assertIn("definition group {\n    relation member: user", schema)
        
        # Since there's a subgroup, parent relation should appear
        self.assertIn("relation parent: group", schema)
       
        # Realm definition with admin role
        self.assertIn("definition realm {\n    relation admin: user", schema)
       
        # Client object definition (app) with read role
        self.assertIn("definition app {\n    relation read: user", schema)

    def test_generate_schema_with_composites(self):
       
        # Realm with a composite role and a base role
        realm = KeycloakRealm(
            name="CompRealm",
            realm_roles=["base", "composite"], 
            client_roles={}, 
            groups=[],
            composite_roles={"composite": ["base"]}
        )
        schema = SchemaGenerator.generate_schema(realm)
       
        # Should have base relation and composite permission in realm definition
        self.assertIn("relation base: user", schema)
        self.assertIn("permission composite = base", schema)
       
        # Composite permission should be inside realm definition
        realm_def_index = schema.index("definition realm")
        perm_index = schema.index("permission composite")
        self.assertGreater(perm_index, realm_def_index)
