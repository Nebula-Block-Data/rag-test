import os
import subprocess
import logging
import glob

import markdown
import telegramify_markdown
import telegramify_markdown.customize as customize
from telegram import Update, MessageEntity
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import shutil
# Import Microsoft GraphRAG API
import graphrag.api as api
import pandas as pd
from graphrag.cli.initialize import initialize_project_at
from graphrag.config.load_config import load_config
from graphrag.index.typing import PipelineRunResult
from pathlib import Path
import asyncio


customize.strict_markdown = False
# Configure logging.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# --------------------
# Helper Functions for Repository & Conversion
# --------------------
def update_repo(local_repo_path: str) -> None:
    """Clone the repository if it doesn't exist, or pull the latest changes."""
    repo_url = os.getenv("REPO_URL")
    if not os.path.exists(local_repo_path):
        logging.info("Cloning repository...")
        subprocess.run(["git", "clone", repo_url, local_repo_path], check=True)
    else:
        logging.info("Repository exists. Pulling latest changes...")
        subprocess.run(["git", "-C", local_repo_path, "pull"], check=True)


def convert_markdown_to_text(input_dir: str, output_dir: str) -> None:
    """
    Convert all Markdown files in the input directory (recursively) to plain-text files.
    Save the resulting .txt files in the output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    md_files = glob.glob(os.path.join(input_dir, "**/*.md"), recursive=True)
    if not md_files:
        logging.error("No markdown files found in %s", input_dir)
        raise ValueError("No markdown files found in input")
    for file in md_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                md_text = f.read()
            html = markdown.markdown(md_text)
            text = " ".join(html.splitlines())
            base = os.path.splitext(os.path.basename(file))[0]
            out_file = os.path.join(output_dir, base + ".txt")
            with open(out_file, "w", encoding="utf-8") as out:
                out.write(text)
        except Exception as e:
            logging.error("Error converting file %s: %s", file, e)
    logging.info("Converted %d markdown files to text in %s.", len(md_files), output_dir)


def copy_specified_files(src_dir: str, dest_dir: str, files_to_copy: list):
    """
    Copy specified files from directory A to directory B. If the file already exists in
    directory B, its content will be overwritten.

    :param src_dir: Source directory path (directory A)
    :param dest_dir: Destination directory path (directory B)
    :param files_to_copy: List of file names to copy
    """
    # Check if the source directory exists
    if not os.path.exists(src_dir):
        print(f"Source directory {src_dir} does not exist!")
        return

    # If the destination directory doesn't exist, create it
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    # Loop through the list of files to copy
    for filename in files_to_copy:
        src_file = os.path.join(src_dir, filename)
        dest_file = os.path.join(dest_dir, filename)

        # Check if the source file exists
        if os.path.exists(src_file):
            try:
                shutil.copy(src_file, dest_file)  # Copy and overwrite if the file exists
                print(f"Copied {src_file} to {dest_file}")
            except Exception as e:
                print(f"Error copying {src_file} to {dest_file}: {e}")
        else:
            print(f"File {src_file} does not exist, skipping.")


# --------------------
# GraphRAG Indexing
# --------------------
async def build_index(project_directory: str, force_build_graph=False):
    """
    Build the GraphRAG index using the provided configuration and query it to retrieve enriched context.
    Skips index building if output files exist (unless FORCE_BUILD_GRAPH is True).
    If test_mode is True, only use a limited set of files for testing.
    """
    setting_yaml = os.path.join(project_directory, "settings.yaml")
    if os.path.exists(setting_yaml):
        print(f"Project already initialized at {project_directory}")
    else:
        # Initialize workspace
        initialize_project_at(project_directory)
        # Use custom config files
        copy_specified_files(os.getcwd(), project_directory, [".env", "settings.yaml"])

    graphRagConfig = load_config(Path(project_directory), Path(setting_yaml))
    graphRagConfig.storage.base_dir = os.path.join(project_directory, "output")
    graphRagConfig.reporting.base_dir = os.path.join(project_directory, "logs")
    graphRagConfig.embeddings.vector_store['db_uri'] = os.path.join(project_directory, "output/lancedb")
    # Determine the input directory based on test mode

    data_dir = "input"
    abs_input_dir = os.path.join(project_directory, data_dir)
    LOCAL_REPO_PATH = os.path.join(project_directory, "doc_repo")
    update_repo(LOCAL_REPO_PATH)
    # Converted text files will be saved under the "input" folder.
    convert_markdown_to_text(LOCAL_REPO_PATH, abs_input_dir)
    logging.info("Using input directory: %s", abs_input_dir)

    # Define output file paths.
    output_folder = os.path.join(project_directory, "output")
    entities_path = os.path.join(output_folder, "create_final_entities.parquet")
    communities_path = os.path.join(output_folder, "create_final_communities.parquet")
    community_reports_path = os.path.join(output_folder, "create_final_community_reports.parquet")

    if not force_build_graph and os.path.exists(entities_path) and os.path.exists(communities_path) and os.path.exists \
                (community_reports_path):
        logging.info("Index already built, skipping index build.")
    else:
        logging.info("Building GraphRAG index...")
        try:
            index_result: list[PipelineRunResult] = await api.build_index(config=graphRagConfig)
            for workflow_result in index_result:
                if workflow_result.errors:
                    logging.error("Workflow '%s' encountered errors: %s", workflow_result.workflow,
                                  workflow_result.errors)
                else:
                    logging.info("Workflow '%s' succeeded. Details: %s", workflow_result.workflow,
                                 workflow_result.__dict__)
        except Exception as e:
            logging.error("Exception during index building: %s", e)
            raise


# --------------------
# GraphRAG Querying Functions
# --------------------
async def query_index(project_directory: str, query: str, search_mode: str):
    """
    Build the GraphRAG index using the provided configuration and query it to retrieve enriched context.
    Skips index building if output files exist (unless FORCE_BUILD_GRAPH is True).
    If test_mode is True, only use a limited set of files for testing.
    """

    graphrag_config = load_config(root_dir=Path(project_directory))
    graphrag_config.storage.base_dir = os.path.join(project_directory, "output")
    graphrag_config.reporting.base_dir = os.path.join(project_directory, "logs")
    graphrag_config.embeddings.vector_store['db_uri'] = os.path.join(project_directory, "output/lancedb")
    # Define index file paths.
    output_folder = os.path.join(project_directory, "output")
    entities_path = os.path.join(output_folder, "create_final_entities.parquet")
    communities_path = os.path.join(output_folder, "create_final_communities.parquet")
    community_reports_path = os.path.join(output_folder, "create_final_community_reports.parquet")
    nodes_path = os.path.join(output_folder, "create_final_nodes.parquet")
    text_units_path = os.path.join(output_folder, "create_final_text_units.parquet")
    relationships_path = os.path.join(output_folder, "create_final_relationships.parquet")

    try:
        entities = pd.read_parquet(entities_path)
        communities = pd.read_parquet(communities_path)
        community_reports = pd.read_parquet(community_reports_path)
        nodes = pd.read_parquet(nodes_path)
        text_units = pd.read_parquet(text_units_path)
        relationships = pd.read_parquet(relationships_path)
    except Exception as e:
        logging.error("Error loading index files: %s", e)
        raise

    if search_mode == 'local':
        print("using local mode to query")
        return await local_search(query, graphrag_config, entities, community_reports, nodes, text_units, relationships)
    elif search_mode == 'global':
        print("using global mode to query")
        return await global_search(query, graphrag_config, entities, communities, community_reports, nodes)
    else:
        logging.error(f"Error not support query mode, %s", search_mode)
        raise


async def global_search(query, graphrag_config, entities, communities, community_reports, nodes):
    try:
        response, context = await api.global_search(
            config=graphrag_config,
            nodes=nodes,
            entities=entities,
            communities=communities,
            community_reports=community_reports,
            community_level=2,
            dynamic_community_selection=False,
            response_type="Multiple Paragraphs",
            query=query,
        )
    except Exception as e:
        logging.error("Error during global search: %s", e)
        raise
    return response, context


async def local_search(query, graphrag_config, entities, community_reports, nodes, text_units, relationships):
    try:
        response, context = await api.local_search(
            config=graphrag_config,
            nodes=nodes,
            entities=entities,
            community_reports=community_reports,
            text_units=text_units,
            relationships=relationships,
            covariates=None,
            community_level=2,
            response_type="Multiple Paragraphs",
            query=query,
        )
    except Exception as e:
        logging.error("Error during local search: %s", e)
        raise
    return response, context


async def handler_data():
    PROJECT_DIRECTORY = os.environ.get("WORK_DIRECTORY", "./ragtest")
    try:
        await build_index(PROJECT_DIRECTORY)
    except Exception as e:
        logging.error("Stopping index processing. Exception: %s", e)
        return


async def process_question(query: str) -> str:
    """
    Process a user question:
      1. Update repository and convert markdown.
      2. Build (if needed) and query the GraphRAG index.
      3. Construct the prompt.
      4. Call Meta Llama3 to generate an answer.
    Returns the answer as a string.
    """
    PROJECT_DIRECTORY = os.environ.get("WORK_DIRECTORY","./ragtest")
    response, context = await query_index(PROJECT_DIRECTORY, query, 'local')
    return response


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the /start command is issued."""
    await update.message.reply_text("Welcome to the SwanChain Bot! Ask me any question about Swan Chain.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process user messages by calling the agent."""
    user_question = update.message.text
    await update.message.reply_text("Processing your question, please wait...")
    try:
        # Call the process_question function from the agent module.
        answer = await process_question(user_question)
        logging.info("answer: %s", answer)
    except Exception as e:
        logging.error("Error processing question: %s", e)
        answer = "There was an error processing your question. Please try again later."
    await update.message.reply_text(text=telegramify_markdown.markdownify(answer), parse_mode="MarkdownV2")


if __name__ == '__main__':
    load_dotenv()  # Load environment variables from .env file
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(handler_data())
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    logging.info("TELEGRAM_BOT_TOKEN: %s", TELEGRAM_BOT_TOKEN)
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Entity(MessageEntity.MENTION), handle_message))
    application.run_polling()
