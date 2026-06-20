import asyncio
from ..services.graph import app, reset_agents
from langchain.tools import tool



@tool("call_publish_team", return_direct=True)
def call_publish_team(task: str):
    """Calls a team of Agents to research and write a post."""
    reset_agents()  # Clear history for each new workflow run
    result = asyncio.run(app.ainvoke({
        "task": task,
        "research_report": "",
        "draft_post": "",
        "review_comments": "",
        "final_post": "",
    }))
    return result.get("final_post", "No post generated")


