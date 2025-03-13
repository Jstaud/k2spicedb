"""
CLI interface for the K2SpiceDB tool.
Allows users to parse Keycloak exports and generate SpiceDB schemas via command line.
"""

import argparse
import sys
import os
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from k2spicedb.keycloak_parser import KeycloakParser
from k2spicedb.llm_transformer import LLMTransformer
from k2spicedb.schema_generator import SchemaGenerator


def setup_logging(verbose: bool):
    """Configures logging level based on verbosity."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s: %(message)s")


def parse_arguments(argv: List[str] = None) -> argparse.Namespace:
    """Parses command-line arguments and returns the parsed namespace."""
    parser = argparse.ArgumentParser(
        prog="k2spicedb",
        description="Generate a SpiceDB schema from Keycloak realm export(s)."
    )
    parser.add_argument("input", nargs="+",
                        help="Path to a Keycloak realm JSON export file or a directory of export files.")
    parser.add_argument("-o", "--output",
                        help="Output file path (for a single input) or directory (for multiple inputs).")
    parser.add_argument("--model", default="text-davinci-003",
                        help="OpenAI model to use for LLM-based schema generation (default: text-davinci-003).")
    parser.add_argument("--no-llm", action="store_true",
                        help="Disable LLM integration and use deterministic schema generation only.")
    parser.add_argument("-j", "--jobs", type=int, default=4,
                        help="Number of files to process in parallel (default: 4). Use 1 to disable concurrency.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging for debugging.")
    return parser.parse_args(argv)


def get_input_files(input_paths: List[str]) -> List[str]:
    """Expands directories into individual JSON files and returns a list of valid input files."""
    files = []
    for path in input_paths:
        if os.path.isdir(path):
            files.extend(os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(".json"))
        else:
            files.append(path)

    if not files:
        logging.error("No valid input files found. Please specify a valid file or directory.")
        sys.exit(1)

    return files


def determine_output_paths(input_files: List[str], output_arg: str):
    """Determines the appropriate output path for single or multiple inputs."""
    if not output_arg:
        if len(input_files) == 1:
            base_name = os.path.splitext(os.path.basename(input_files[0]))[0]
            return None, os.path.join(os.path.dirname(input_files[0]), f"{base_name}.zed")

        return os.getcwd(), None  # 🔥 Ensure it does not return `None, None`

    if len(input_files) > 1:
        if os.path.exists(output_arg) and not os.path.isdir(output_arg):
            logging.error("Output path must be a directory when processing multiple input files.")
            sys.exit(1)

        os.makedirs(output_arg, exist_ok=True)
        return output_arg, None

    return None, output_arg or os.path.join(os.getcwd(), "output.zed")  # 🔥 Ensure output_file is never empty


def process_file(input_path: str, output_path: str, parser_obj, transformer):
    """Processes a single Keycloak export file, generating and saving the SpiceDB schema."""
    try:
        logging.info("Processing: %s", input_path)
        realm = parser_obj.parse_file(input_path)

        schema_text = transformer.transform(realm) if transformer else SchemaGenerator.generate_schema(realm)

        if not schema_text.strip():
            logging.warning("Skipping empty schema for realm '%s'", realm.name)
            return False

        if not output_path.strip():  # 🔥 Check if output_path is empty or blank
            logging.error("Output path is empty! This should never happen.")
            return False

        abs_output_path = os.path.abspath(output_path)  # 🔥 Convert to absolute path
        print(f"DEBUG: Writing to absolute path: {abs_output_path}")

        os.makedirs(os.path.dirname(abs_output_path), exist_ok=True)  # Ensure directory exists

        with open(abs_output_path, "w", encoding="utf-8") as f:
            f.write(schema_text)

        logging.info("Schema saved: %s", abs_output_path)
        return True
    except Exception as e:
        logging.error("Failed to process %s: %s", input_path, e)
        return False


def main(argv: List[str] = None) -> int:
    """Main function for handling CLI execution."""
    args = parse_arguments(argv)
    setup_logging(args.verbose)

    input_files = get_input_files(args.input)
    output_dir, output_file = determine_output_paths(input_files, args.output)

    print(f"DEBUG: output_dir={output_dir}, output_file={output_file}")  # 🔥 Debug print

    if output_file is None and output_dir is None:
        logging.error("Both output_dir and output_file are None. This should never happen.")
        sys.exit(1)
    parser_obj = KeycloakParser()
    transformer = None if args.no_llm else LLMTransformer(model_name=args.model)

    if not args.no_llm and os.getenv("OPENAI_API_KEY") is None:
        logging.warning("OPENAI_API_KEY environment variable is not set. OpenAI API calls may fail.")

    # Process files (sequentially or with concurrency)
    results = []
    if len(input_files) > 1 and args.jobs > 1:
        with ThreadPoolExecutor(max_workers=min(args.jobs, len(input_files))) as executor:
            future_to_path = {
                executor.submit(
                    process_file,
                    path,
                    os.path.join(output_dir, os.path.splitext(os.path.basename(path))[0] + ".zed"),  # ✅ Corrected naming
                    parser_obj,
                    transformer
                ): path for path in input_files
            }
            results = [future.result() for future in as_completed(future_to_path)]
    else:
        for path in input_files:
            out_path = output_file if len(input_files) == 1 else os.path.join(output_dir, os.path.splitext(os.path.basename(path))[0] + ".zed")
            results.append(process_file(path, out_path, parser_obj, transformer))

    success_count = sum(results)
    fail_count = len(results) - success_count
    logging.info("Processing complete. Successful: %d, Failed: %d.", success_count, fail_count)
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())