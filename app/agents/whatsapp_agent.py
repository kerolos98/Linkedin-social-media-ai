from .skeleton import LangchainAgent
from app.services.agentic_tools import call_publish_team
class ExcutiveAgent(LangchainAgent):
    with open("app/templates/excutive.md", "r", encoding="utf-8") as f:
        identity = f.read()
    def __init__(self, servers, identity):
        super().__init__(servers, identity) 
        self.local_tools.append(call_publish_team)
