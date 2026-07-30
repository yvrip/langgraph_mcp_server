import os
import asyncio
from load_dotenv import load_dotenv
from typing_extensions import TypedDict, NotRequired
from typing import Annotated, Any
from config_google import configura_credenciais_google

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain.agents.middleware.types import InputAgentState
from langchain_core.messages.utils import convert_to_openai_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import add_messages

load_dotenv()
configura_credenciais_google()

memory = InMemorySaver()

class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    config: dict[str, Any]
    response: NotRequired[str]

def agent_prompt():
    template = '''You are an advanced AI assistant with access to various tools. You will:
        1. Analyze each user query and decide if a tool is needed.
        2. If so, invoke it immediately using the specified format—not in narrative.
        3. If not, answer directly.
        4. When the user asks something that relies on prior chat or known facts check the given previous conversation, tool response and assistance response before calling any tools or asking user for an input.
    '''
    return template

async def run_memory_chat(state: GraphState):
    
    # create a MultiServerMCPClient with the specified tools and their configurations
    client = MultiServerMCPClient(
        {
            "servicos-bcb-tools": {
                "url": "http://localhost:8125/mcp",
                "transport": "streamable_http",
            },
            "brasilapi-tools": {
                "url": "http://localhost:8124/mcp",
                "transport": "streamable_http",
            },
        }
    )
    
    # get the available tools from the server
    tools = await client.get_tools()

    # define the agent with access to the tools, llm, memory
    agent = create_agent(
        "google_vertexai:gemini-2.5-flash",
        tools,
        checkpointer=memory,
        system_prompt=agent_prompt()
    )

    # formatting the input message structure
    formatted_messages = InputAgentState(messages=state["messages"][-1:])

    # trigger the agent and return the formatted response
    response = await agent.ainvoke(
        formatted_messages,
        RunnableConfig(**state["config"])
    )
    response = convert_to_openai_messages(response['messages'])

    return {"messages": response, "response": response[-1]['content']}

if __name__ == "__main__":

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        # Initialize the graph state with the user's message
        graph_state = GraphState(
            messages=[HumanMessage(content=user_input)],
            config={"configurable": {"thread_id": "default"}}
        )

        # Run the agent with the current graph state
        result = asyncio.run(run_memory_chat(graph_state))

        # Print the agent's response
        print(f"Agent: {result['response']}")