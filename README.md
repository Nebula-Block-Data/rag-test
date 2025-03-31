### Config `.env`
```
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

### Setup build and compile environment
```bash
# Create a virtual environment  
python3 -m venv myenv

# Install package
pip install -r requirements.txt
```

### Start graph_rag and telegram bot 
```
#!/bin/bash
python3 main.py >> server.log 2>&1 &
```

### User case:
Log in to telegram and ask questions through @bot.
