import os
import re

from dotenv import load_dotenv
from openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from custom_tools.tools import asigned_tools, search_law_by_pdf
from custom_tools.load_data import read_text_file
from filtering.search_by_kipris import CodeSearchKipris
from filtering.identify_simple_filtering import result_by_simple_test

load_dotenv(verbose=True)
OPENAI_API_KEY = os.getenv('_OPENAI_API_KEY')
standards_trademark = read_text_file()

def extract_reason(text):
    # Use regex to find the Reason section
    match = re.search(r"Reason:\s*(.*)", text, re.DOTALL)
    if match:
        return match.group(1).strip()  # Extract the reason text
    return ""


def main_gpt(template):
    client = OpenAI(
        api_key=OPENAI_API_KEY,
    )

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an AI agent specialized in smartly and reliably analyzing the potential for trademark registrations of particular brands, following the Trademark Examination Guidelines."},
            {
                "role": "user",
                "content": template
            }
        ],
        temperature=0.0
    )

    response = completion.choices[0].message.content
    return response

def extract_status(text):
    # Use regular expression to search for "status" or "Status" followed by any text until the end of line
    status_match = re.search(r'(?i)status:\s*(.*)', text)  # (?i) makes the regex case-insensitive
    return status_match.group(1).strip() if status_match else None

def final_execute_gpt(application_code, input_brand):

    application_status_value = None

    _application_info = CodeSearchKipris(title=input_brand, application_code=application_code, single_flag=True)
    _application_info._search_by_code()
    _application_info._search_by_application_code()
    application_info = _application_info.to_dict()
    print("\n\n\n\n\napplication_info:",application_info)
    application_status_value = application_info.pop('application_status')
    _similar_application_info = CodeSearchKipris(title=input_brand, application_code=application_code, single_flag=False)
    _similar_application_info._search_by_code()
    _similar_application_info._search_by_application_code()
    similar_application_info = _similar_application_info.to_dict()
    print("\n\n\n\n\nsimilar_application_info:",similar_application_info)

    result = []

    # Determine codes based on the presence of similar application info
    if not similar_application_info.get('applicant_name'):
        codes = [2]
    else:
        similar_application_info = result_by_simple_test(application_info, similar_application_info)
        print("\n\n\n\n\nsimilar_application_info:", similar_application_info)
        codes = [1, 2]
    
    for code in codes[:-1]:
        template = generate_gpt_template(application_info, similar_application_info, code)
        each_result = main_gpt(template)
        # reason_text = extract_reason(each_result) 
        formatted_result = f"--- Result for Code {code} ---\n{each_result}\n"
        print(formatted_result)
        result.append(formatted_result)

        if code == 1:
            if "pending" in each_result.lower():
                result.pop()
                continue
            elif "reject" in each_result.lower():
                final_template = generate_gpt_template(application_info, similar_application_info, code)
                final_result = main_gpt(final_template)
                return final_result
            elif "approve" in each_result.lower():
                result.pop()
                result.append("출원인이 같기 때문에 승인되어야 함")
                final_template = generate_gpt_template(application_info, similar_application_info, code)
                final_result = main_gpt(final_template)
                return application_status_value, final_result            
    
    final_template = generate_gpt_template(application_info, similar_application_info, 2, result=result)
    final_result = main_gpt(final_template)
    result.append(f"--- Final Result ---\n{final_result}\n")
    print(final_result)
    return application_status_value, final_result


def main_agent(application_code, input_brand):
    _application_info = CodeSearchKipris(title=input_brand, application_code=application_code, single_flag=True)
    _application_info._search_by_code()
    _application_info._search_by_application_code()

    application_info = _application_info.to_dict()

    _similar_application_info = CodeSearchKipris(title=input_brand, application_code=application_code, single_flag=False)
    _similar_application_info._search_by_code()
    _similar_application_info._search_by_application_code()

    similar_application_info = _similar_application_info.to_dict()

    if not similar_application_info['application_code'] or not similar_application_info['applicant_name']:
        final_result = final_excute_agent(application_info, "No search results.")
    else:
        similar_application_info = result_by_simple_test(application_info, similar_application_info)
        final_result = final_excute_agent(application_info, similar_application_info)
        
    return final_result


def final_excute_agent(application_info, similar_application_info):

    input_brand = application_info.get('title')

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.00001,
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
                "You are an AI agent specialized in smartly and reliably analyzing the potential for trademark registrations of particular brands, following the Trademark Examination Guidelines."
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


def generate_gpt_template(application_info, similar_application_info, code, result=""):
    """
    Generates a template for GPT based on the given code.
    
    Parameters:
    - code = 1: Check for similar trademarks (if similar_application_info is present).
    - code = 2: Check for distinctiveness of the trademark name.
    - code = 3: Verify compliance with trademark examination criteria.
    """

    title = application_info['title']
    template = ""

    if code == 1:
        template = f"""
        Please evaluate the trademark registration eligibility of "{title}" based on the following criteria.

        1. Similar Trademark Analysis
        - Start by checking the "patent information search service" results for "{title}":
        - Input trademark: "{application_info}"
        - Search Results: {similar_application_info}
        
        Guidelines-
        - Automatic Approval for Similar Registered Trademarks: If the "applicant_name" in "Input trademark" matches an applicant who has already registered a highly similar trademark approve this application without further review or exceptions.
        - Similarity Based on Name Only: Determine trademark similarity solely based on the trademark name; ignore the applicant’s identity in this assessment.
        - Temporary Approval for Non-Matching Codes: If the trademark names are similar but 'similar_code_match' is 'False', the application can receive temporary "pending"

        Please provide the output in the following format:
        Reason: [Provide specific and accurate reasons]
        Status: [Only write "approve", "pending" or "reject"]
        """

    elif code == 2:
        template = f"""
            Please evaluate the trademark registration eligibility of "{title}" based on the following criteria and provide a response with specific and accurate reasoning grounded in the trademark examination standards.

            1. If any related precedents are applicable, please reference them and provide a detailed explanation based on those precedents. [{standards_trademark}]

            ** Please use the following format for your response:
            Reason: []
            Trademark Status: [Only Write approve or reject]
        """
    
    return template

def generate_template(input_brand, application_info):

    template =f'''
    Please go through each criterion in the  "Cautions When Judging" of Trademark Examination Guidelines one by one and confirm whether "{input_brand}" meets the standards for approval.

    Trademark Information = [{application_info}]

    "The trademark examination criteria are broad, so please consider them in three separate sections."
    **Trademark Examination Guidelines = [{standards_trademark}]**

    "Please answer without using tools."

    Fill out the trademark application in the following format.

    Trademark status: (Must you choose between O(approve) or X(reject))
    Reason:
    '''
    return template
    
# "Please answer without using tools."
# If there is an identical trademark by the same applicant, the application is permissible
# final_execute_gpt('4020190102212', '건강하고 맛있는 치킨! 삼계치킨 GINSENG CHICKEN')
# final_execute_gpt('4020190027144', '살 빼주는 언니')
# final_execute_gpt('4020190018027', '어른이놀이터')
# final_execute_gpt('4020190095000', '포모나')

# final_execute_gpt('4020190051360', '현자의 돌 생활과 윤리')
# final_execute_gpt('4020190087323', '하프밀')
# final_execute_gpt('4020190068309', '대성자동문')
# final_execute_gpt('4020190054525', '아마존펫')
# final_execute_gpt('4020190053381', '통일한의원')
# final_execute_gpt('4020190015159', '당신의 피부혈액형은 무엇입니까?')
# final_execute_gpt('4020190067029', 'simplus')

# print(main_agent('4020190068309', '대성자동문')['output'])
# print(main_agent('4020190054525', '아마존펫')['output'])
# print(main_agent('4020190087323', '하프밀')['output'])
# print(main_agent('4020190053381', '통일한의원')['output'])
# final_execute_gpt('4020190084056', '좋은 집 좋은 자재')
# final_execute_gpt('4020190099709', '메이크케어')
# final_execute_gpt('4020190109038', '자연 담은 유리병')
# final_execute_gpt('4020190087323', '하프밀')


# print(main_agent('4020190015159', '당신의 피부혈액형은 무엇입니까?')['output'])
# print(main_agent('4020190084056', '좋은 집 좋은 자재')['output']) # 좋은 집 좋은 자재
# print(main_agent('4020190099709', '메이크케어')['output']) # 메이크케어
# print(main_agent('4020190109038', "자연 담은 유리병")['output']) # 자연 담은 유리병
# main_gpt()
# print("타입:", main_agent('4020190109038')['output'])
# main_gpt('대성자동문')
# main_gpt('통일한의원')