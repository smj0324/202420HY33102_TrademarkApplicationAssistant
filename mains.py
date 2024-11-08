import os
import json
from openai import OpenAI
import openai
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
from filtering.identify_simple_filtering import result_by_simple_test


load_dotenv(verbose=True)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

standards_trademark = load_json_law_guidelines()


def main_gpt(application_code, input_brand):
    _application_info = CodeSearchKipris(application_code=application_code, single_flag=True)
    _application_info._search_by_code()
    _application_info._search_by_application_code()

    application_info = _application_info.to_dict()

    _similar_application_info = CodeSearchKipris(title=input_brand, single_flag=False)
    _similar_application_info._search_by_code()
    _similar_application_info._search_by_application_code()

    similar_application_info = _similar_application_info.to_dict()

    if not similar_application_info['application_code']:
        final_result = {
            "output": final_excute_gpt(input_brand, application_info, similar_application_info),
            "application_info": application_info,
            "similar_application_info": "No search results."
        }
    else:
        final_result = {
            "output": final_excute_gpt(input_brand, application_info, similar_application_info),
            "application_info": application_info,
            "similar_application_info": similar_application_info
        }
        
    #print("*"*50)
    #print(application_info)
    #print("*"*50)
    #print(similar_application_info)
    return final_result

def final_excute_gpt(input_brand, application_info, similar_application_info):
    # 프롬프트 내용 구성
    prompt_content = (
        f" 상표심사기준과 다음 내용을 참고하여, 네가 심사위원이 되어서 상표명에 대한 출원 가능성을 판별해줘:\n\n"
        f"{generate_template(input_brand, application_info, similar_application_info)}"
    )

    # OpenAI ChatCompletion API 호출
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a legal expert in trademark law."},
            {"role": "user", "content": prompt_content}
        ],
        max_tokens=2000,  # 답변 길이 제어
        temperature=0  # 낮은 temperature로 결정적인 답변 생성
    )

    # 답변 텍스트 반환
    return response.choices[0].message.content.strip()

def main_agent(application_code, input_brand):
    _application_info = CodeSearchKipris(application_code=application_code, single_flag=True)
    _application_info._search_by_code()
    _application_info._search_by_application_code()

    application_info = _application_info.to_dict()

    _similar_application_info = CodeSearchKipris(title=input_brand, single_flag=False)
    _similar_application_info._search_by_code()
    _similar_application_info._search_by_application_code()

    similar_application_info = _similar_application_info.to_dict()

    if not similar_application_info['application_code']:
        final_result = final_excute_agent(application_info, "No search results.")
    else:
        similar_application_info = result_by_simple_test(application_info, similar_application_info)
        final_result = final_excute_agent(application_info, similar_application_info[0])
        
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
                "You are an AI agent who smartly and accurately examines the possibility of applying for a trademark to a particular brand."
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
    Please go through each criterion in the  "판단시 유의사항" of Trademark Examination Guidelines one by one and confirm whether {input_brand} meets the standards for approval, If there is a highly similar trademark registered by the same applicant, this application should be considered permissible as a primary criterion.

    Trademark Information = [{application_info}],

    Trademark Examination Guidelines = [{standards_trademark}]
    Search results for "patent information search service" of "{input_brand}" = {similar_application_info},

    Please fill out the trademark application in the following format.
    등록 상태: (Must you choose between 승인 or 거절)
    이유:
    '''

    return template
    
# "Please answer without using tools."
# If there is an identical trademark by the same applicant, the application is permissible

print(main_gpt('4020230020425', '탑퓨전포차 무한리필')['output']) # 탑퓨전포차 무한리필
#print(main_gpt('4020190084056', '좋은 집 좋은 자재')['output']) # 좋은 집 좋은 자재
#print(main_gpt('4020190099709', '메이크케어')['output']) # 메이크케어
#print(main_gpt('4020190109038', "자연 담은 유리병")['output']) # 자연 담은 유리병

# print("타입:", main_agent('4020190109038')['output'])

