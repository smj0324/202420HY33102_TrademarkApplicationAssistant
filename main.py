import os
import json
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from custom_tools.tools import asigned_tools
from custom_tools.load_data import load_json_law_guidelines
from filtering.search_by_kipris import CodeSearchKipris


load_dotenv(verbose=True)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

standards_trademark = load_json_law_guidelines()


def main_agent(application_code):
    _application_info = CodeSearchKipris(application_code=application_code, single_flag=True)
    _application_info._search_by_code()
    _application_info._search_by_application_code()

    application_info = _application_info.to_dict()

    _similar_application_info = CodeSearchKipris(title=application_info.get('title'), single_flag=False)
    _similar_application_info._search_by_code()
    _similar_application_info._search_by_application_code()

    similar_application_info = _similar_application_info.to_dict()

    final_result = final_excute_agent(application_info, similar_application_info)

    return final_result


def final_excute_agent(application_info, similar_application_info):

    input_brand = application_info.get('title')

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=None,
        timeout=None,
        api_key=OPENAI_API_KEY,
    )

    tools = asigned_tools()
    llm_with_tools = llm.bind_tools(tools)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "An AI assistant that intelligently and accurately informs users about the registration status of a trademark application for a specified brand in korea."
            ),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
        }
        | prompt
        | llm_with_tools
        | OpenAIToolsAgentOutputParser()
    )


    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
    )

    final_result = agent_executor.invoke({
        "input": f"{generate_template(input_brand, application_info, similar_application_info)}"
    })

    return final_result



def generate_template(input_brand, application_info, similar_application_info):

    template =f'''
    Please check the application status of {input_brand} based on 
    the 'Trademark Examination Guidelines' below and 
    inform us whether the application is approved or not in Korean.
    
    Trademark Information = {application_info},
    Search results for "patent information search service" of "{input_brand}" = {similar_application_info},
    Trademark Examination Guidelines = ""

    Registration status: (Must you choose between 승인 or 거절)
    Reason:
    '''

    return template


# print(main_agent('4520160002952'))
print('*'*50)
print(main_agent('4020190099709'))
