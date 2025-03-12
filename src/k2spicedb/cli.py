"""
CLI interface for the K2SpiceDB tool.
Allows users to parse Keycloak exports and generate SpiceDB schemas via command line.
"""

import argparse
import sys
import os
import logging
from typing import List

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
        # Default output naming
        if len(input_files) == 1:
            base_name = os.path.splitext(os.path.basename(input_files[0]))[0]
            return None, os.path.join(os.path.dirname(input_files[0]), f"{base_name}.zed")
        return os.getcwd(), None  # Default to current directory for multiple files

    if len(input_files) > 1:
        if os.path.exists(output_arg) and not os.path.isdir(output_arg):
            logging.error("Output path must be a directory when processing multiple input files.")
            sys.exit(1)

        os.makedirs(output_arg, exist_ok=True)
        return output_arg, None

    return None, output_arg


def process_file(input_path: str, output_path: str, parser_obj, transformer):
    """Processes a single Keycloak export file, generating and saving the SpiceDB schema."""
    try:
        logging.info(f"Processing: {input_path}")
        realm = parser_obj.parse_file(input_path)

        schema_text = transformer.transform(realm) if transformer else SchemaGenerator.generate_schema(realm)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(schema_text)

        logging.info(f"Schema saved: {output_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to process {input_path}: {e}")
        return False


def main(argv: List[str] = None) -> int:
    """Main function for handling CLI execution."""
    args = parse_arguments(argv)
    setup_logging(args.verbose)

    input_files = get_input_files(args.input)
    output_dir, output_file = determine_output_paths(input_files, args.output)

    parser_obj = KeycloakParser()
    transformer = None if args.no_llm else LLMTransformer(model_name=args.model)

    if not args.no_llm and os.getenv("OPENAI_API_KEY") is None:
        logging.warning("OPENAI_API_KEY environment variable is not set. OpenAI API calls may fail.")

    # Process files (sequentially or with concurrency)
    results = []
    if len(input_files) > 1 and args.jobs > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(args.jobs, len(input_files))) as executor:
            future_to_path = {executor.submit(process_file, path, os.path.join(output_dir, os.path.basename(path) + ".zed"), parser_obj, transformer): path
                              for path in input_files}
            results = [future.result() for future in as_completed(future_to_path)]
    else:
        for path in input_files:
            out_path = output_file if len(input_files) == 1 else os.path.join(output_dir, os.path.basename(path) + ".zed")
            results.append(process_file(path, out_path, parser_obj, transformer))

    success_count = sum(results)
    fail_count = len(results) - success_count
    logging.info(f"Processing complete. Successful: {success_count}, Failed: {fail_count}.")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
