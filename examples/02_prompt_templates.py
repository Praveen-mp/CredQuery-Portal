from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models import init_chat_model
load_dotenv()
template = ChatPromptTemplate(
    [
        ("system", "You are a helpful AI bot. Your name is {name}."),
        ("human", "Hello, how are you doing?"),
        ("ai", "I'm doing well, thanks!"),
        ("human", "{user_input}"),
    ]
)


prompt_value = template.invoke(
    {
        "name": "Bob",
        "user_input": "What is your name?",
    }
)

llm = init_chat_model(
    "azure_openai:gpt-4.1-mini-pat",
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)

chain = template | llm | StrOutputParser()

response_1 = chain.invoke({"name": "Bob", "user_input": "What is your name?"})
print("Response 1:", response_1)

response_2 = chain.invoke({"name": "Bob", "user_input": "Can you tell me a fun fact about the ocean?"})
print("Response 2:", response_2)

batch_responses = chain.batch([
    {"name": "Bob", "user_input": "What's 12 times 8?"},
    {"name": "Bob", "user_input": "Name one benefit of using LCEL."},
])
print("Batch responses:", batch_responses)

