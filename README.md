# K2SpiceDB

K2SpiceDB is a migration tool that transforms Keycloak realm configurations into optimized SpiceDB schemas using a LangChain-powered LLM agent. Instead of a simple 1:1 schema migration, K2SpiceDB leverages AI to generate improved database schemas, considering performance, security, and maintainability enhancements.

## 🚀 Features
- **LLM-powered schema optimization** – Uses OpenAI's API via LangChain to refine and enhance the schema.
- **Automated Keycloak to SpiceDB migration** – Parses Keycloak realm exports and intelligently generates equivalent SpiceDB schemas.
- **Configurable AI model** – Allows customization of the LLM behavior via prompt templates.
- **Dockerized for easy deployment** – Ready to run in containerized environments.

## 📂 Project Structure
```
k2spicedb/
├── .gitignore
├── CONTRIBUTING.md
├── Dockerfile
├── LICENSE
├── README.md
├── keycloak_to_spicedb_architecture.md
├── poetry.lock
├── pyproject.toml
├── requirements.txt
├── setup.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── README.md
├── examples/
│   ├── example_keycloak_export.json
│   └── example_spicedb_schema.zed
├── scripts/
│   └── export_realm.sh
├── src/
│   └── k2spicedb/
│       ├── __init__.py
│       ├── cli.py
│       ├── llm_transformer.py
│       ├── parser.py
│       ├── prompt_handler.py
│       ├── schema_generator.py
│       └── transformer.py
└── tests/
    ├── test_cli.py
    ├── test_parser.py
    └── test_transformer.py
```

## 🛠️ Installation
### **Prerequisites**
- Python 3.12+
- Poetry
- Docker (optional for containerized deployment)

### **Setup**
Clone the repository and install dependencies:
```sh
git clone https://github.com/your-repo/k2spicedb.git
cd k2spicedb
poetry install
```

Set up your environment variables (e.g., OpenAI API key):
```sh
export OPENAI_API_KEY="your-api-key-here"
```

## 🔧 Usage
### **Running the Migration**
To migrate a Keycloak realm configuration into a SpiceDB schema:
```sh
poetry run python -m k2spicedb.transformer --input realm-config.json --output spicedb-schema.zed
```

### **Running Tests**
Ensure your changes work as expected:
```sh
poetry run pytest
```

## 🐳 Docker Deployment
Build and run the container:
```sh
docker build -t k2spicedb .
docker run -e OPENAI_API_KEY=your-api-key -v $(pwd)/output:/app/output k2spicedb
```

## 📜 License
This project is licensed under the MIT License.

## 👥 Contributors
- James Staud ([@Jstaud](https://github.com/jstaud))

