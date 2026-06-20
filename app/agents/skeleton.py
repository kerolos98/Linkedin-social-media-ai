from dotenv import load_dotenv

import os
load_dotenv("app/agents/.env")

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_litellm import ChatLiteLLM


MODEL_CHAIN = [

    # === REASONING / GENERAL ===

    # === NVIDIA NEMOTRON (all free) ===
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",     # 1M context, agent tasks
    "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",        # Efficient MoE, 256K context
    "openrouter/nvidia/nemotron-3-nano-omni-30b-a3b:free",   # Multimodal, 256K context
    "openrouter/nvidia/nemotron-nano-9b-v2:free",            # Reasoning + non-reasoning, 128K
    "openrouter/nvidia/nemotron-nano-12b-v2-vl:free",        # OCR/doc intelligence, 128K

    # === GOOGLE GEMMA 4 ===
    "openrouter/google/gemma-4-31b-it:free",          # Multimodal, 262K context
    "openrouter/google/gemma-4-26b-a4b-it:free",      # MoE variant, fast, 262K context

    # === OTHER ===
    "openrouter/z-ai/glm-4.5-air:free",               # Lightweight, 131K context
    "openrouter/nousresearch/hermes-3-llama-3.1-405b:free",  # Generalist, 131K context
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",     # Fallback general use

    # === AUTO-ROUTER (picks best available free model) ===
    "openrouter/openrouter/free",
    "openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "openrouter/nex-agi/nex-n2-pro:free",
    "openrouter/google/gemma-4-26b-a4b-it:free"
    #""ollama_chat/qwen3:0.6b"
]


def build_model(model_name: str, rout=None):
    if rout == "openrouter":
        return ChatLiteLLM(
            model=model_name,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            api_base="https://openrouter.ai/api/v1",
            temperature=0,
        )

    elif rout == "ollama_chat":
        return ChatLiteLLM(
            model=model_name,
            api_base="http://localhost:11434",
            temperature=0,
        )


class LangchainAgent:

    def __init__(
        self,
        servers=None,
        identity="",
        local_tools=None
    ):

        self.servers = servers or {}
        self.identity = identity

        self.client = (
            MultiServerMCPClient(self.servers)
            if self.servers
            else None
        )

        self.local_tools = local_tools or []

        self.tools = []
        self.agent = None

        self.model_index = 0
        self.message_history = []  # Store conversation history

    async def init(self):

        self.tools = []

        # MCP tools
        if self.client:
            mcp_tools = await self.client.get_tools()
            self.tools.extend(mcp_tools)

        # Local Python tools
        self.tools.extend(self.local_tools)

        print(f"Loaded tools: {len(self.tools)}")
        print("Tool names:")

        for tool in self.tools:
            try:
                print(f" - {tool.name}")
            except Exception:
                print(f" - {tool}")


    def _get_model(self):

        model_name = MODEL_CHAIN[self.model_index]
        self.rout = model_name.split("/")[0]

        print(f"\n🧠 Using model: {model_name}\n")

        return build_model(model_name, self.rout)

    def _switch_model(self):

        self.model_index += 1

        if self.model_index >= len(MODEL_CHAIN):
            raise Exception(
                "❌ All models failed (rate limit or API error)"
            )

        print(
            f"🔁 Switching to next model: "
            f"{MODEL_CHAIN[self.model_index]}"
        )

    def _extract(self, content):

        if isinstance(content, str):
            return content

        if isinstance(content, list):

            texts = []

            for item in content:

                if isinstance(item, dict):
                    if item.get("type") == "text":
                        texts.append(item.get("text", ""))

                else:
                    texts.append(str(item))

            return "\n".join(texts)

        return str(content)

    async def run_prompt(self, prompt: str):

        if self.agent is None:
            await self.init()

        # Add user message to history
        self.message_history.append(("user", prompt))

        for _ in range(len(MODEL_CHAIN)):

            try:

                self.agent = create_agent(
                    model=self._get_model(),
                    tools=self.tools,
                )
                
                # Build messages with history + system identity
                messages = [("system", self.identity)]
                messages.extend(self.message_history)
                
                result = await self.agent.ainvoke({
                    "messages": messages
                })

                for msg in reversed(result["messages"]):

                    if msg.__class__.__name__ in ["AIMessage","ToolMessage"]:
                        if msg.__class__.__name__ == "ToolMessage":
                            print(f"\n🛠️ Tool used: {msg.name}\n")
                            response = self._extract(msg.content)
                        else:
                            response = self._extract(msg.content)
                        
                        # Add assistant response to history
                        self.message_history.append(("assistant", response))
                        return response

            except Exception as e:

                print(
                    f"\n❌ Model failed: "
                    f"{MODEL_CHAIN[self.model_index]}"
                )

                print(f"Reason: {e}\n")

                self._switch_model()

        return None
    
    def clear_history(self):
        """Clear conversation history (e.g., for new chat session)."""
        self.message_history = []