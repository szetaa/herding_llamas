from langchain.agents import load_tools
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain.agents import Tool
from langchain.utilities import DuckDuckGoSearchAPIWrapper

from llm_langchain import LlmLangchain

llm = LlmLangchain()

tools = load_tools(["llm-math"], llm=llm)

search = DuckDuckGoSearchAPIWrapper()
# search = GoogleSerperAPIWrapper()
duck_search = Tool(
    name="Duck Duck Go Search",
    func=search.run,
    description="A wrapper around DuckDuckGo Search. Useful for when you need to answer questions about current events. The input is the question to search relavant information.",
)

tools = [duck_search]


PREFIX = """Answer the following questions as best you can. You have access to the following tools:"""
FORMAT_INSTRUCTIONS = """Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question"""
SUFFIX = """Begin!

Question: {input}
Thought:{agent_scratchpad}"""


agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    agent_kwargs={
        "prefix": PREFIX,
        "format_instructions": FORMAT_INSTRUCTIONS,
        "suffix": SUFFIX,
    },
)

agent.run("<your question here that requires one or more web searches>")
