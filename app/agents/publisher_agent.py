from .skeleton import LangchainAgent
from app.services.linkedin_tools import post_to_linkedin
class PublisherAgent(LangchainAgent):
    with open("app/templates/publisher_agent.md", "r", encoding="utf-8") as f:
        identity = f.read()
    def __init__(self, servers, identity):
        super().__init__(servers, identity) 
        self.local_tools.append(post_to_linkedin)
