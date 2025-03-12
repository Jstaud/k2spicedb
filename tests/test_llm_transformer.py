import unittest
from k2spicedb.keycloak_parser import KeycloakRealm
from k2spicedb.llm_transformer import LLMTransformer

# Disable logging in tests
import logging
logging.disable(logging.CRITICAL)

class DummyLLM:
    """Dummy LLM for testing LLMTransformer without calling external API."""
    def __init__(self, fail=False):
        self.fail = fail
        self.last_prompt = None
    def __call__(self, prompt):
        # Store the prompt for inspection
        self.last_prompt = prompt
        if self.fail:
            # Simulate a failure in the LLM call
            raise Exception("Simulated LLM failure")
        # Return a dummy schema text
        return "dummy schema output"
    # For compatibility with LangChain interface, define predict similarly
    def predict(self, prompt):
        return self.__call__(prompt)

class TestLLMTransformer(unittest.TestCase):
    def test_transform_with_dummy_llm(self):
        # Prepare a simple realm input
        realm = KeycloakRealm(
            name="DummyRealm",
            realm_roles=["role1"],
            client_roles={},
            groups=[]
        )
        dummy_llm = DummyLLM(fail=False)
        transformer = LLMTransformer(llm=dummy_llm)
        result = transformer.transform(realm)
        # The result should be whatever the dummy LLM returns
        self.assertEqual(result, "dummy schema output")
        # The prompt passed to the LLM should contain the realm name and role name
        self.assertIn("DummyRealm", dummy_llm.last_prompt)
        self.assertIn("role1", dummy_llm.last_prompt)

    def test_transform_fallback_on_failure(self):
        # Prepare a realm with minimal data
        realm = KeycloakRealm(name="X", realm_roles=["r1"], client_roles={}, groups=[])
        dummy_llm = DummyLLM(fail=True)  # this LLm will raise an exception
        transformer = LLMTransformer(llm=dummy_llm)
        result = transformer.transform(realm)
        # Since dummy LLM fails, the transformer should fallback to SchemaGenerator
        # The fallback output should at least contain a "definition user"
        self.assertIn("definition user", result)
        # Should also contain the realm role 'r1' as a relation in realm object (sanitized)
        self.assertIn("relation r1:", result)
