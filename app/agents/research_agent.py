import asyncio
from .skeleton import LangchainAgent
from app.services.servers import WEBSEARCH
class ResearchAgent(LangchainAgent):
    with open("app/templates/research_agent.md", "r", encoding="utf-8") as f:
        identity = f.read()
    def __init__(self, servers, identity):
        super().__init__(servers=WEBSEARCH, 
                         identity=identity) 

if __name__ == "__main__":
    agent = ResearchAgent(servers=[], identity=ResearchAgent.identity)
    result = asyncio.run(agent.run_prompt("What are the latest solutions for medical comding with AI for healthcare providers?"))
    print(result)