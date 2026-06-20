import asyncio
from typing import TypedDict

from ..agents.writer_agent import WriterAgent
from ..agents.research_agent import ResearchAgent
from ..agents.critic_agent import CriticAgent
from langgraph.graph import StateGraph, END

writer = WriterAgent(servers={}, identity=WriterAgent.identity)
researcher = ResearchAgent(servers={}, identity=ResearchAgent.identity)
critic = CriticAgent(servers={}, identity=CriticAgent.identity)


def log(title, data):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print(data)
    print("=" * 70 + "\n")

class State(TypedDict):
    task: str
    research_report: str
    draft_post: str
    review_comments: str
    final_post: str

def extract_text(result):

    if isinstance(result, str):
        return result

    if isinstance(result, list):

        text = []

        for item in result:

            if isinstance(item, dict):

                if item.get("type") == "text":
                    text.append(item.get("text", ""))

        return "\n".join(text)

    return str(result)

async def research_node(state: State):
    research_task = f"Research the following topic and provide a detailed report:\n\n{state['task']}"
    research_report = await researcher.run_prompt(research_task)
    state['research_report'] = extract_text(research_report)
    log("Research Report", state['research_report'])
    return state

async def draft_post_node(state: State):
    draft_task = (
        "Summarize the following research report into a polished LinkedIn post. "
        "Use the key insights, keep the tone engaging and professional, "
        "and make it ready for publishing as a standalone post:\n\n"
        f"{state['research_report']}"
    )
    draft_post = await writer.run_prompt(draft_task)
    state['draft_post'] = extract_text(draft_post)
    log("Draft Post", state['draft_post'])
    return state

async def review_node(state: State):
    review_task = (
        "Review the following LinkedIn post and suggest concrete improvements "
        "for clarity, engagement, accuracy, and professionalism:\n\n"
        f"{state['draft_post']}"
    )
    review_comments = await critic.run_prompt(review_task)
    state['review_comments'] = extract_text(review_comments)
    log("Review Comments", state['review_comments'])
    return state

async def final_post_node(state: State):
    final_post_task = (
        "Write the final LinkedIn post using the draft post and critic review. "
        "Incorporate the feedback, polish the language, and return only the finished post text:\n\n"
        f"Draft post:\n{state['draft_post']}\n\n"
        f"Critic review:\n{state['review_comments']}\n\n"
        f"Research report:\n{state['research_report']}"
    )
    final_post = await writer.run_prompt(final_post_task)
    state['final_post'] = extract_text(final_post)
    log("Final LinkedIn Post", state['final_post'])
    return state

graph = StateGraph(State)
graph.add_node("research", research_node)
graph.add_node("draft_post", draft_post_node)
graph.add_node("review", review_node)
graph.add_node("final_post", final_post_node)
graph.set_entry_point("research")
graph.add_edge("research", "draft_post")
graph.add_edge("draft_post", "review")
graph.add_edge("review", "final_post")
graph.add_edge("final_post", END)

def reset_agents():
    """Clear history for all agents before starting a new workflow."""
    writer.clear_history()
    researcher.clear_history()
    critic.clear_history()

app = graph.compile()