"""
LLM transformer module.
Uses LangChain to integrate with the OpenAI API for enhancing schema generation.
"""
import logging
import os
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

from k2spicedb.keycloak_parser import KeycloakRealm
from k2spicedb.schema_generator import SchemaGenerator

logger = logging.getLogger(__name__)

class LLMTransformer:
    """
    Uses a language model to transform Keycloak realm data into a SpiceDB schema.
    By default, integrates with OpenAI via LangChain.
    """
    def __init__(self, model_name: str = "o3-mini", temperature: float = 0.0, 
                 max_tokens: int = 1000, openai_api_key: str = None, llm=None):
        """
        Initialize the LLM transformer.
        :param model_name: OpenAI model name (e.g., 'o3-mini' or 'gpt-4.5').
        :param temperature: Sampling temperature for the LLM (0.0 for deterministic output).
        :param max_tokens: Maximum tokens for the LLM output.
        :param openai_api_key: OpenAI API key (if None, will use OPENAI_API_KEY env var).
        :param llm: (For testing) an optional custom LLM instance to use instead of creating one.
        """
        self.model_name = model_name
        if llm is not None:
            # Allow injecting a custom LLM (for testing or alternative LLMs)
            self.llm = llm
            # Try to store model name if available on custom LLM
            if hasattr(llm, "model_name"):
                self.model_name = llm.model_name
        else:
            # Choose appropriate LangChain LLM class based on model type (completion vs chat)
            if model_name.startswith("gpt-") or model_name.startswith("GPT-"):
                # Use OpenAI Chat model (e.g., GPT-4.5)
                self.llm = ChatOpenAI(model_name=model_name, temperature=temperature, 
                                      max_tokens=max_tokens, openai_api_key=openai_api_key)
            else:
                # Use completion model
                self.llm = OpenAI(model_name=model_name, temperature=temperature, 
                                  max_tokens=max_tokens, openai_api_key=openai_api_key)

    def transform(self, realm: KeycloakRealm) -> str:
        """
        Transform the parsed KeycloakRealm data into a SpiceDB schema using an LLM.
        :param realm: KeycloakRealm object with parsed realm data.
        :return: A string containing the SpiceDB schema definition.
        """
        # Build prompt detailing the realm's roles and groups
        details_lines = []
        # List realm roles and client roles
        if realm.realm_roles:
            details_lines.append("- Realm roles: " + ", ".join(realm.realm_roles))
        for client, roles in realm.client_roles.items():
            details_lines.append(f"- Client '{client}' roles: " + ", ".join(roles))
        # List composite role composition if any
        for comp, parts in realm.composite_roles.items():
            if parts:
                realm_part_names = [p for p in parts if ":" not in p]
                client_parts_map: Dict[str, List[str]] = {}
                for p in parts:
                    if ":" in p:
                        client_name, role_name = p.split(":", 1)
                        client_parts_map.setdefault(client_name, []).append(role_name)
                comp_desc_segments = []
                if realm_part_names:
                    comp_desc_segments.append("realm roles [" + ", ".join(realm_part_names) + "]")
                for client_name, roles_list in client_parts_map.items():
                    comp_desc_segments.append(f"{client_name} roles [" + ", ".join(roles_list) + "]")
                comp_desc = " and ".join(comp_desc_segments)
                details_lines.append(f"- Composite role '{comp}' includes " + comp_desc)
        # List groups (indicate subgroups if present)
        if realm.groups:
            group_info = []
            for group in realm.groups:
                if group.subgroups:
                    sub_names = [sub.name for sub in group.subgroups]
                    group_info.append(f"{group.name} (subgroups: " + ", ".join(sub_names) + ")")
                else:
                    group_info.append(group.name)
            details_lines.append("- Groups: " + ", ".join(group_info))
        # Combine details into prompt text
        details_text = "\n".join(details_lines) if details_lines else "(No roles or groups)"
        prompt_text = (
            f"Keycloak realm '{realm.name}' has the following roles and groups:\n"
            f"{details_text}\n\n"
            "Generate a SpiceDB schema definition that represents the above roles and groups.\n"
            "- Define object types for users, groups, and any resources corresponding to clients.\n"
            "- Include relations for group membership and role assignments (using role names as relation or permission names).\n"
            "- If a role is composite or groups have subgroups, represent those relationships (e.g., permissions that combine other roles or a parent-child relation for groups).\n"
            "Output *only* the SpiceDB schema (object definitions) without additional explanation."
        )
        try:
            logger.info(f"Generating schema via LLM for realm '{realm.name}' using model '{self.model_name}'.")
            logger.debug(f"LLM prompt for realm '{realm.name}':\n{prompt_text}")
            # Invoke the LLM (OpenAI or ChatOpenAI) with the prompt
            if hasattr(self.llm, "predict"):
                # For LangChain LLMs that provide a predict method (completions)
                result = self.llm.predict(prompt_text)
            elif "ChatOpenAI" in self.llm.__class__.__name__:
                # For chat models, send the prompt as a single human message
                response = self.llm([HumanMessage(content=prompt_text)])
                result = response.content if hasattr(response, "content") else str(response)
            else:
                # Fallback: call the LLM instance directly
                result = self.llm(prompt_text)
            schema_text = result.strip()
            logger.info(f"LLM schema generation completed for realm '{realm.name}'.")
            return schema_text
        except Exception as e:
            logger.error(f"LLM transformation failed for realm '{realm.name}': {e}")
            # Fallback to deterministic schema generation
            schema_text = SchemaGenerator.generate_schema(realm)
            logger.info(f"Falling back to programmatic schema generation for realm '{realm.name}'.")
            return schema_text
