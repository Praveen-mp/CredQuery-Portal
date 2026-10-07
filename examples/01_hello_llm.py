import os
from dotenv import load_dotenv
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

# Load environment variables from .env file
load_dotenv()

# 1. Initialize the Azure OpenAI model using the unified interface
# Format: "azure_openai:base_model_name" or map the configuration explicitly
llm = init_chat_model(
    "azure_openai:gpt-4o-mini", # Fallback fallback name or direct target
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)

# 2. Define a custom tool for the agent
@tool
def multiply_numbers(a: int, b: int) -> int:
    """Multiply two integers together."""
    return a * b

tools = [multiply_numbers]

# 3. Create the agent with the Azure LLM
system_prompt = "You are a helpful mathematical assistant deployed on Azure."
agent = create_agent(model=llm, tools=tools, system_prompt=system_prompt)

# 4. Run the query loop
query = "What is 256 multiplied by 4?"
print(f"User: {query}\n")

response = agent.invoke({
    "messages": [
        {"role": "user", "content": query}
    ]
})

# Print the agent's final text response
print(f"Agent: {response['messages'][-1].content}")