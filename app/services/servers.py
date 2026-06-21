from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()

# 1. Exa Web Search Server (Remote MCP)
WEBSEARCH = {
    "exa": {
        "transport": "stdio",
        "command": "npx",
        "args": [
            "-y",
            "mcp-remote",
            f"https://mcp.exa.ai/mcp?apiKey={os.getenv('EXA_API_KEY')}"
        ]
    }
}

# 2. Filesystem Server (Replaced Docker with native @modelcontextprotocol/server-filesystem)
FILESYSTEM = {
    "filesystem": {
        "transport": "stdio",
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            os.getcwd()  # Grants access to your current working directory natively
        ]
    }
}

# 3. LinkedIn Server (Replaced Docker with native npx execution)
LINKEDIN = {
    "linkedin": {
        "transport": "stdio",
        "command": "npx",
        "args": [
            "-y",
            "mcp-server-linkedin-company"  # Standard npm package variant
        ],
        # Explicitly passing environment variables to the native process
        "env": {
            "LINKEDIN_TOKEN": os.getenv("LINKEDIN_TOKEN"),
            "LINKEDIN_ORG_ID": os.getenv("LINKEDIN_ORG_ID"),
            "PATH": os.getenv("PATH") # Keeps system path so 'npx' can be found
        }
    }
}