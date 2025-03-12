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

def main(argv: List[str] = None) -> int:
    """
    Main entry point for the CLI.
    :param argv: List of command-line arguments (for testing). If None, uses sys.argv.
    :return: Exit code (0 for success, 1 for error).
    """
    parser = argparse.ArgumentParser(
        prog="k2spicedb",
        description="Generate SpiceDB schema from Keycloak realm export(s)."
    )
    parser.add_argument(
        "input", nargs="+",
        help="Path to a Keycloak realm JSON export file or a directory of export files."
    )
    parser.add_argument(
        "-o", "--output", help="Output file path (for single input) or directory (for multiple inputs)."
    )
    parser.add_argument(
        "--model", default="text-davinci-003",
        help="OpenAI model to use for LLM-based schema generation (default: text-davinci-003)."
    )
    parser.add_argument(
        "--no-llm", action="store_true",
        help="Disable LLM integration and use deterministic schema generation only."
    )
    parser.add_argument(
        "-j", "--jobs", type=int, default=4,
        help="Number of files to process in parallel (default: 4). Use 1 to disable concurrency."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging for debugging."
    )
    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s: %(message)s")

    # Resolve input file list
    input_paths: List[str] = []
    for inp in args.input:
        if os.path.isdir(inp):
            # If directory, add all JSON files within (non-recursive for simplicity)
            for filename in os.listdir(inp):
                if filename.lower().endswith(".json"):
                    input_paths.append(os.path.join(inp, filename))
        else:
            input_paths.append(inp)
    if not input_paths:
        logging.error("No input files found. Please specify a valid file or directory.")
        return 1

    # Determine output path(s)
    output_dir = None
    output_file_single = None
    if args.output:
        if len(input_paths) > 1:
            # Multiple inputs require output to be a directory
            if os.path.exists(args.output) and not os.path.isdir(args.output):
                logging.error("Output path must be a directory when multiple input files are provided.")
                return 1
            output_dir = args.output
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception as e:
                    logging.error(f"Could not create output directory '{output_dir}': {e}")
                    return 1
        else:
            # Single input
            if os.path.isdir(args.output):
                output_dir = args.output
            else:
                output_file_single = args.output
    else:
        # No explicit output path: use default naming
        if len(input_paths) == 1:
            # Single file: put output next to input with .zed extension
            inp = input_paths[0]
            base_name = os.path.splitext(os.path.basename(inp))[0]
            output_file_single = os.path.join(os.path.dirname(inp), base_name + ".zed")
        else:
            # Multiple files: use current directory for outputs
            output_dir = os.getcwd()

    # Prepare parser and (optionally) LLM transformer
    parser_obj = KeycloakParser()
    transformer = None
    if not args.no_llm:
        transformer = LLMTransformer(model_name=args.model)
        # Warn if no API key in environment
        if os.getenv("OPENAI_API_KEY") is None:
            logging.warning("OPENAI_API_KEY environment variable not set. OpenAI API calls may fail.")
    else:
        logging.info("LLM integration disabled; using deterministic schema generation.")

    # Define processing of a single file (to use in loop or thread pool)
    def process_file(input_path: str) -> bool:
        try:
            logging.info(f"Processing realm export: {input_path}")
            realm = parser_obj.parse_file(input_path)
            # Generate schema (use LLM if available, else fallback)
            if transformer:
                schema_text = transformer.transform(realm)
            else:
                schema_text = SchemaGenerator.generate_schema(realm)
            # Determine output file path
            if output_dir:
                base = os.path.splitext(os.path.basename(input_path))[0]
                out_path = os.path.join(output_dir, base + ".zed")
            else:
                out_path = output_file_single
            # Write schema to output file
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(schema_text)
            logging.info(f"Schema for realm '{realm.name}' written to: {out_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to process '{input_path}': {e}")
            return False

    # Process files (with concurrency if applicable)
    results = []
    if len(input_paths) > 1 and args.jobs and args.jobs > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        num_workers = min(args.jobs, len(input_paths))
        logging.info(f"Using concurrency: {num_workers} threads")
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_path = {executor.submit(process_file, path): path for path in input_paths}
            for future in as_completed(future_to_path):
                res = future.result()
                results.append(res)
    else:
        # Process sequentially
        for path in input_paths:
            res = process_file(path)
            results.append(res)

    # Summary and exit code
    success_count = sum(1 for r in results if r)
    fail_count = len(results) - success_count
    logging.info(f"Processing complete. Successful: {success_count}, Failed: {fail_count}.")
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
