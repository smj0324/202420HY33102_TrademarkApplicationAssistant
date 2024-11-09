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
from custom_tools.tools import asigned_tools
from custom_tools.load_data import load_json_law_guidelines
from filtering.search_by_kipris import CodeSearchKipris
from filtering.identify_simple_filtering import result_by_simple_test

load_dotenv(verbose=True)
OPENAI_API_KEY = os.getenv('_OPENAI_API_KEY')
standards_trademark = load_json_law_guidelines()

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
        temperature=0
    )

    response = completion.choices[0].message.content
    return response

def final_execute_gpt(application_code, input_brand):
    _application_info = CodeSearchKipris(title=input_brand, application_code=application_code, single_flag=True)
    _application_info._search_by_code()
    _application_info._search_by_application_code()
    application_info = _application_info.to_dict()
    print("\n\n\n\n\napplication_info:",application_info)
    _similar_application_info = CodeSearchKipris(title=input_brand, application_code=application_code, single_flag=False)
    _similar_application_info._search_by_code()
    _similar_application_info._search_by_application_code()
    similar_application_info = _similar_application_info.to_dict()

    result = []

    # Determine codes based on the presence of similar application info
    if not similar_application_info.get('application_code') or not similar_application_info.get('applicant_name'):
        codes = [2, 3, 4]
    else:
        similar_application_info = result_by_simple_test(application_info, similar_application_info)
        codes = [1, 2, 3, 4]
    
    for code in codes[:-1]:
        template = generate_gpt_template(application_info, similar_application_info, code)
        each_result = main_gpt(template)
        reason_text = extract_reason(each_result) 
        formatted_result = f"--- Result for Code {code} ---\n{each_result}\n"
        print(formatted_result)
        result.append(formatted_result)
        
        # Check for rejection in the current result
        if "reject" in each_result.lower():
            if code == 1:
                # Immediate return if code 1 produces a rejection
                final_template = generate_gpt_template(application_info, similar_application_info, code)
                final_result = main_gpt(final_template)
                return final_result
            else:
                continue
    
    # If no rejections for code 1 or if all codes complete, compile and return final result
    final_template = generate_gpt_template(application_info, similar_application_info, 4, result=result)
    final_result = main_gpt(final_template)
    result.append(f"--- Final Result ---\n{final_result}\n")
    print(final_result)
    return final_result



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
        
        - Guidelines:
            1. If a highly similar trademark is already registered by the same applicant, this application must be approved without exception. In such cases, ignore any other considerations—this trademark must be approved.
            2. Check similarity based only on the trademark name, not the applicant. 
            3. If 'similar_code_match' is False, treat the trademarks as different and **approve** the application.

        2. Output Format:
        Predict Status: choice approve or reject
        Reason: [Do not state whether the application is approved or rejected in the rationale. Only mention approval if the applicant is the same as an existing registered trademark.]
        """


    elif code == 2:
        template = f"""
            Please evaluate the trademark registration eligibility of "{title}" based on the following criteria.

            1. Distinctiveness Evaluation:
            - Assess whether "{title}" has unique qualities that set it apart from common terms or widely known references.
            - For internationally known brands, consider if the Korean translation or pronunciation closely resembles the trademark name. For instance, "스노우 화이트 (Snow White)" may not be widely recognized, but "백설공주" is very familiar in Korea.

            2. Component Analysis:
            - If you identify a main part in the name, briefly describe its overall meaning.
            - If the name includes culturally significant references, consider whether this familiarity could enhance or diminish its distinctiveness, possibly creating new, non-confusing associations in the intended market.

            3. Example of Acceptable Separations:
            - 미래테크놀로지 → 미래 + 테크놀로지
            - 삼성전자서비스 → 삼성전자 + 서비스
            - 네이버클라우드 → 네이버 + 클라우드
            - 현대 → 현대
            - 인스타그램 → 인스타그램

            4. Additional Considerations:
            - Avoid separating components if it would alter or dilute the intended meaning of the trademark.
            - If the main part of the name represents a well-known brand not owned by the applicant, note this, as it could lead to rejection due to potential free-riding.
            - If the trademark name is overly generic, it may also be subject to rejection.

            **Output Format**:
            Predict Status: choice approve or reject
            Reason: [Do not state whether the application is approved or rejected in the rationale.]
        """

    elif code == 3:
        template = f"""
        Please verify the trademark registration eligibility of "{title}" according to the Trademark Examination Guidelines.

        Trademark Examination Guidelines:
        - As the guidelines are extensive, please divide them into parts for a thorough review of each section.
        - Assess whether "{title}" meets the criteria by considering the unique impression it may create for the relevant goods or services, particularly in the market where it will be applied.
        - Evaluate whether common or well-known terms in the name have been used creatively or in a way that could avoid misleading associations while still conveying a distinct identity.

        **Trademark Examination Standards**: [{standards_trademark}]

        **Output Format**:
        Predict Status: choice approve or reject
        Reason: [Do not state whether the application is approved or rejected in the rationale.]
        """

    elif code == 4:
        detailed_results = "\n".join([f"Result for Code {i+1}: {res}" for i, res in enumerate(result)])
        template = f"""
        1. Please make a comprehensive conclusion based on the results of each examination, 
        If "Result for Code Code 1" finds that a similar trademark is already registered by the same applicant, this application must be approved without exception.
        
        Note: While Code 1 > Code 3 > Code 2 may generally indicate the relative importance of criteria, this order is flexible and should not limit the assessment.

        Detailed Examination Results:
        {detailed_results}
        
        Please provide the output in the following format:
        Trademark Status: (Must choose between approve or reject)
        Reason: [Your summary reason here]
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
# final_execute_gpt('4020190066112', '모두웰')
# final_execute_gpt('4020190027144', '살 빼주는 언니')
# final_execute_gpt('4020190018027', '어른이놀이터')
# final_execute_gpt('4020190051360', '현자의 돌 생활과 윤리')
# final_execute_gpt('4020190087323', '하프밀')
# final_execute_gpt('4020190068309', '대성자동문')
# final_execute_gpt('4020190054525', '아마존펫')
# final_execute_gpt('4020190053381', '통일한의원')
# final_execute_gpt('4020190015159', '당신의 피부혈액형은 무엇입니까?')
# final_execute_gpt('4020190006385', '버드리')

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