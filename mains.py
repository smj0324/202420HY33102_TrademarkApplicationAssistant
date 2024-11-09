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
    print(application_info)
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

    reason_text = ""
    
    for code in codes[:-1]:
        template = generate_gpt_template(application_info, similar_application_info, code, result=reason_text)
        each_result = main_gpt(template)
        reason_text = extract_reason(each_result) 
        formatted_result = f"--- Result for Code {code} ---\n{each_result}\n"
        result.append(formatted_result)
        print(formatted_result)
        
        # Check for rejection in the current result
        if "reject" in each_result.lower():
            if code == 1:
                # Immediate return if code 1 produces a rejection
                final_template = generate_gpt_template(application_info, similar_application_info, code)
                final_result = main_gpt(final_template)
                return final_result
            else:
                # Skip the current result if rejection is found for codes other than 1
                continue
    
    # If no rejections for code 1 or if all codes complete, compile and return final result
    final_template = generate_gpt_template(application_info, similar_application_info, code, result=result)
    final_result = main_gpt(final_template)
    print(f"--- Final Result ---\n{final_result}\n")
    result.append(f"--- Final Result ---\n{final_result}\n")
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
        - Search Result: {similar_application_info}
        - If a highly similar trademark is already registered by the same applicant, consider this application permissible.
        - Note: Identical or similar trademarks do not infringe if the designated goods or services differ, except if the registered trademark is well-known.

        2.Output Format:
        Predict Status: choice approve or reject
        Reason: [Your summary reason here. If the applicant is the same as an existing registered trademark, emphasize that this application should be approved without exception.]
        """


    elif code == 2:
        template = f"""
        Please evaluate the trademark registration eligibility of "{title}" based on the following criteria.
        Reference: {result}
        
        - Determine whether "{title}" has distinctive qualities that differentiate it from common terms or well-known references.
        
        - For brands well-known internationally, it is important to assess whether the Korean translation or pronunciation closely resembles the trademark name. For example, "스노우 화이트(snow white)" might not be widely recognized, but "백설공주" is very familiar in Korea.
        - If you identify a main part of the name, briefly describe its overall meaning. Avoid separating parts if this would weaken the brand’s unique impression.
        - If the name includes culturally significant references, assess whether this familiarity could enhance or reduce the brand’s distinctiveness. Consider if these associations might create new, non-confusing impressions in the intended market.
        
        - Example Separations:
            - 미래테크놀로지 → 미래 + 테크놀로지
            - 삼성전자서비스 → 삼성전자 + 서비스
            - 네이버클라우드 → 네이버 + 클라우드
            - 현대 → 현대
            - 인스타그램 → 인스타그램

        - Determine if separating components would alter or weaken the intended meaning.
        - If a main part is identified, describe its overall meaning. Avoid separation if it dilutes the brand(trademark)’s unique impression.
        - If the main part represents a well-known brand(trademark) not owned by the applicant, note this as it may lead to rejection due to potential free-riding.

        Additioinaly, If it is a trademark name in a too general sense, it may be rejected.

        **Output Format**:
        Predict Status: choice approve or reject
        Reason: [Your Summary reason here]
        """

    elif code == 3:
        template = f"""
        Please verify the trademark registration eligibility of "{title}" according to the Trademark Examination Guidelines.
        Reference: {result}

        Trademark Examination Guidelines:
        - As the guidelines are extensive, please divide them into parts for a thorough review of each section.
        - Assess whether "{title}" meets the criteria by considering the unique impression it may create for the relevant goods or services, particularly in the market where it will be applied.
        - Evaluate whether common or well-known terms in the name have been used creatively or in a way that could avoid misleading associations while still conveying a distinct identity.

        **Trademark Examination Standards**: [{standards_trademark}]

        **Output Format**:
        Predict Status: choice approve or reject
        Reason: [Your Summary reason here]
        """
        # For final result compilation after all codes
        if result and code > 3:
            detailed_results = "\n".join([f"Result for Code {i+1}: {res}" for i, res in enumerate(result)])
            template = f"""
            Based on the results of each examination criterion, please predict the Registration Status.

            If there is a previous registration by the same applicant, approval is guaranteed.
            Detailed examination results:
            {detailed_results}

            Please provide the output in the following format:
            Trademark status: (Must choose between approve or reject)
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
final_execute_gpt('4020190006385', '버드리')

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