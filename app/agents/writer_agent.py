from .skeleton import LangchainAgent
from app.services.servers import WEBSEARCH
class WriterAgent(LangchainAgent):
    with open("app/templates/writer_agent.md", "r", encoding="utf-8") as f:
        identity = f.read()
    def __init__(self, servers, identity):
        super().__init__(servers=WEBSEARCH, identity=identity) 
