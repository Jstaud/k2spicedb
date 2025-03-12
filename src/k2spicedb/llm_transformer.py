# src/k2spicedb/llm_transformer.py
from langchain import LLMChain, PromptTemplate
from langchain.llms import OpenAI

class LLMTransformer:
    def __init__(self, openai_api_key: str, temperature: float = 0.3):
        self.llm = OpenAI(api_key=openai_api_key, temperature=temperature)
        self.prompt_template = PromptTemplate(
            template=(
                "You are a schema migration expert. Given the following Keycloak realm configuration:\n\n"
                "{keycloak_config}\n\n"
                "Generate an improved SpiceDB schema. Consider performance, security, and maintainability improvements. "
                "Include comments explaining your decisions."
            ),
            input_variables=["keycloak_config"]
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)

    def transform(self, keycloak_config: str) -> str:
        """Transforms a Keycloak realm configuration into an improved SpiceDB schema."""
        result = self.chain.run(keycloak_config=keycloak_config)
        return result

# Example usage:
if __name__ == "__main__":
    # This is just for local testing. In production, use environment variables to handle API keys.
    import os
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")

    # Load your Keycloak realm config (could be from a file or parser)
    keycloak_config = """
    {
      "realm": "example",
      "users": [...],
      "roles": [...],
      "clients": [...]
    }
    """
    transformer = LLMTransformer(openai_api_key=key)
    improved_schema = transformer.transform(keycloak_config)
    print("Improved SpiceDB Schema:\n", improved_schema)
