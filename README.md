# RAG-test

**RAG-test** is a demo project that builds a Retrieval-Augmented Generation (RAG) service using NebulaBlock's inference and embedding models. This can serve as a starting point to create your own RAG-powered applications, such as customer service bots, community assistants, or intelligent document Q&A systems.

## Features

- Utilizes NebulaBlock's hosted LLM and embedding models
- Easily configurable via environment variables
- Telegram bot integration for interactive Q&A
- Customizable document source via GitHub repo
- Scalable and adaptable to various RAG-based use cases

---

## Configuration

Create a `.env` file in the root directory and fill in the following values:

```env
WORK_DIRECTORY="ragtest"
REPO_URL="https://github.com/Nebula-Block-Data/docs"
TELEGRAM_BOT_TOKEN=""

LLM_API_KEY=""
LLM_MODEL="meta-llama/Llama-3.3-70B-Instruct"
LLM_API_BASE="https://inference.nebulablock.com/v1"

EMBEDDING_API_KEY=""
EMBEDDING_MODEL="togethercomputer/m2-bert-80M-2k-retrieval"
EMBEDDING_API_BASE="https://inference.nebulablock.com/v1"
```

> Replace the API keys and tokens with your actual credentials.

---

## Setup & Run

### Create Environment and Install Dependencies

```bash
# Create a virtual environment
python3 -m venv myenv
source myenv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Start the RAG Service and Telegram Bot

```bash
# Start the main service in the background
python3 main.py >> server.log 2>&1 &
```

---

## How to Use

1. Launch the service as described above.
2. Open Telegram and find your bot using `@your_bot_username`.
3. Ask questions — the bot will retrieve relevant info from the specified GitHub repo and generate accurate, contextual answers.

---

## Customization Tips

- Change `REPO_URL` to use a different documentation or knowledge source.
- Swap models by editing `LLM_MODEL` and `EMBEDDING_MODEL` in `.env`.
- You can extend this demo into a full web-based application using Flask, FastAPI, or any frontend framework of your choice.

---

## License

MIT License
