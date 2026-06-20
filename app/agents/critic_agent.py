from .skeleton import LangchainAgent
class CriticAgent(LangchainAgent):
    with open("app/templates/critic_agent.md", "r", encoding="utf-8") as f:
        identity = f.read()
    def __init__(self, servers, identity):
        super().__init__(servers, identity) 
