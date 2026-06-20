from dotenv import load_dotenv
import os
load_dotenv()
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
FILESYSTEM = {
    "filesystem": {
        "transport": "stdio",
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "-v",
            f"{os.getcwd()}:/workspace",
            "mcp/filesystem",
            "/workspace"
        ]
    }
}
LINKEDIN = {
    "linkedin": {
        "transport": "stdio",
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "-e", f"LINKEDIN_TOKEN={os.getenv('LINKEDIN_TOKEN')}",
            "-e", f"LINKEDIN_ORG_ID={os.getenv('LINKEDIN_ORG_ID')}",
            "mcp/linkedin-company"
        ]
    }
}
MEDIUM = {
    "medium": {
        "transport": "stdio",
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "-e", f"MEDIUM_TOKEN={os.getenv('MEDIUM_TOKEN')}",
            "mcp/medium"
        ]
    }
}