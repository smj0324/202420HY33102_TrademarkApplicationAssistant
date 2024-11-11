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
OPENAI_API_KEY = os.getenv('OPENAI_API_KEYs')
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
        
    print("*"*50)
    print(application_info)
    print("*"*50)
    print(similar_application_info)

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

    template = f'''
    "{input_brand}" 상표의 출원 가능성을 단계별로 검토해줘. 상표 심사 기준에 따라 다음과 같은 항목을 검토해야 해.
    먼저 상표 심사 기준을 알려줄게.\n {standards_trademark}\n\n

    1. 유사 상표 분석:
    - "{input_brand}"에 대해 "특허 정보 검색 서비스"의 유사 상표 결과를 확인해줘.
    - 입력된 상표 정보: {application_info}\n
    - 유사 상표 검색 결과: {similar_application_info}\n
    
    유사 상표 분석 시 고려할 점:
    - 동일 출원인에 의해 등록된 유사 상표가 있을 경우, 해당 출원은 무조건 승인되어야 함.
    - 상표명만을 기준으로 유사성을 확인하며, 출원인을 기준으로 하지 않음.
    - 지정 상품의 '유사 코드 매칭'이 다를 경우, 임시 승인이 가능함.
    - 입력된 상표와 검색 결과에 동일한 '유사 코드명'이 존재하는 경우, 해당 출원은 거절됨.\n\n
    
    2. 독창성 확인:
    - "{input_brand}"의 상표명에 독창성이 있는지 상표 심사 기준에 따라 검토해줘.
    - 독창성을 판단할 때, 법적 조항과 관련 사례를 활용하여 이유를 명확히 설명해줘.\n\n
    
    3. 적합성 확인:
    - 상표 심사 기준에 따른 "{input_brand}"의 적합성을 검토해줘.
    - 상표 심사 기준을 검토하여 "{input_brand}"가 지정된 상품이나 서비스에 대해 식별력을 갖추고 있는지 확인해줘.\n\n
    
    4. 종합 결론 도출:
    - 각 검토 단계의 결과를 바탕으로 종합적인 결론을 내려줘.
    - 유사 상표 분석에서 동일 출원인의 유사 상표가 등록된 경우, 다른 기준과 관계없이 해당 출원은 승인되어야 해.

    다음의 형식을 지켜서 답변해줘.
    등록 상태: (승인 또는 거절 중 하나 선택)
    이유: [검토 결과를 바탕으로 이유를 설명]
    '''

    return template

    # f'''
    # "{input_brand}" 상표의 출원 가능성을 단계별로 검토해보고 답변해줘. 상표 심사 기준에 따라 다음과 같은 항목을 검토해야 해.
    # 먼저 상표 심사 기준을 알려줄게.\n {standards_trademark}\n\n

    # 0. 심사 기준 확인: 
    # - "{input_brand}"의 상표명이 심사기준에 적합하는지 꼼꼼하게 확인해야해. 
    # 상표법 제33조부터 제34조까지의 각 항목과 사례를 검토해서 판단해줘. 
    
    # 1. 유사 상표 분석:
    # - "{input_brand}"에 대해 "특허 정보 검색 서비스"의 유사 상표 결과를 확인해줘.
    # - 입력된 상표 정보: {application_info}\n
    # - 유사 상표 검색 결과: {similar_application_info}\n
    
    # 유사 상표 분석 시 고려할 점:
    # - 다른 출원인에 의해 등록된 유사 상표가 있을 경우, 유사도와 나머지 항목을 고려하여 결정해야해.
    # - 상표명만을 기준으로 유사성을 확인하며, 출원인을 기준으로 하지 않음.
    # - 'similar_code_match'가 'False'일 경우, 임시 승인.
    # - 'similar_code_name list'에 있는 요소 중 입력으로 들어간 상표명과 겹치는 경우가 있다면, 출원 거절
    # \n\n
    
    # 2. 독창성 확인:
    # - "{input_brand}"의 상표명에 독창성이 있는지 상표 심사 기준에 따라 검토해줘.
    # - 독창성을 판단할 때, 법적 조항과 관련 사례를 활용하여 이유를 명확히 설명해줘.\n\n
    
    # 3. 적합성 확인:
    # - 상표 심사 기준에 따른 "{input_brand}"의 적합성을 검토해줘.
    # - 상표 심사 기준을 검토하여 "{input_brand}"가 지정된 상품이나 서비스에 대해 식별력을 갖추고 있는지 확인해줘.\n\n
    
    # 4. 종합 결론 도출:
    # - 각 검토 단계의 결과를 바탕으로 종합적인 결론을 내려줘.
    # - 0번 항목의 심사기준을 가장 중요하게 고려해야해.
    # - 그러나 유사 상표 분석에서 동일 출원인의 유사 상표가 등록된 경우, 다른 기준과 관계없이 해당 출원은 무조건 승인되어야 해.
    
    # 답변은 다음의 형식으로만 작성해줘.
    # 등록 상태: (승인 또는 거절 중 하나 선택)
    # 이유: (0-4번 검토 결과를 바탕으로 이유를 설명)
    # '''
    #13개/7개 정답 프롬프트 
    # f'''
    # "{input_brand}" 상표의 출원 가능성을 단계별로 검토해줘. 상표 심사 기준에 따라 다음과 같은 항목을 검토해야 해.
    # 먼저 상표 심사 기준을 알려줄게.\n {standards_trademark}\n\n

    # 1. 유사 상표 분석:
    # - "{input_brand}"에 대해 "특허 정보 검색 서비스"의 유사 상표 결과를 확인해줘.
    # - 입력된 상표 정보: {application_info}\n
    # - 유사 상표 검색 결과: {similar_application_info}\n
    
    # 유사 상표 분석 시 고려할 점:
    # - 동일 출원인에 의해 등록된 유사 상표가 있을 경우, 해당 출원은 무조건 승인되어야 함.
    # - 상표명만을 기준으로 유사성을 확인하며, 출원인을 기준으로 하지 않음.
    # - 지정 상품의 '유사 코드 매칭'이 다를 경우, 임시 승인이 가능함.
    # - 입력된 상표와 검색 결과에 동일한 '유사 코드명'이 존재하는 경우, 해당 출원은 거절됨.\n\n
    
    # 2. 독창성 확인:
    # - "{input_brand}"의 상표명에 독창성이 있는지 상표 심사 기준에 따라 검토해줘.
    # - 독창성을 판단할 때, 법적 조항과 관련 사례를 활용하여 이유를 명확히 설명해줘.\n\n
    
    # 3. 적합성 확인:
    # - 상표 심사 기준에 따른 "{input_brand}"의 적합성을 검토해줘.
    # - 상표 심사 기준을 검토하여 "{input_brand}"가 지정된 상품이나 서비스에 대해 식별력을 갖추고 있는지 확인해줘.\n\n
    
    # 4. 종합 결론 도출:
    # - 각 검토 단계의 결과를 바탕으로 종합적인 결론을 내려줘.
    # - 유사 상표 분석에서 동일 출원인의 유사 상표가 등록된 경우, 다른 기준과 관계없이 해당 출원은 승인되어야 해.

    # 다음의 형식을 지켜서 답변해줘.
    # 등록 상태: (승인 또는 거절 중 하나 선택)
    # 이유: [검토 결과를 바탕으로 이유를 설명]
    # '''

    

# template =f'''
#     "{input_brand}"가 상표 출원이 가능한지 확인하고 싶어. 
#     상표심사기준은 다음과 같아.\n\n {standards_trademark} \n
#     "{input_brand}"이 식별력이 있는지는 상표심사기준의 법과 사례 등을 꼼꼼하게 따져봐야해.
#     예를들어, 상표명에 유명 브랜드가 포함되어 있는지, 지명이 포함되어 있는지, 성질표시가 포함되어 있는지 등을 따져볼 필요가 있어. \n\n

#     "{input_brand}"에 대한 정보는 다음과 같아. [{application_info}]\n
    
#     다음은 "{input_brand}"와 유사한 상표에 대한 정보야.\n [{similar_application_info}]\n\n
#     "{input_brand}" 가 식별력이 있는 상표인지, 타인의 선등록 상표가 있는지, 지정상품이 동일하거나 유사한지 등 여러 정보를 종합하여 판단해줘.
#     유사한 상표가 있더라도, 출원인이 같을 경우 등록이 가능할 수 있어.

#     그리고 다음 형식으로 답변해줘.
#     등록 상태: (Must you choose between 승인 or 거절)
#     이유:

#     '''
    
# f'''
#     Please go through each criterion in the  "판단시 유의사항" of Trademark Examination Guidelines one by one and confirm whether {input_brand} meets the standards for approval, If there is a highly similar trademark registered by the same applicant, this application should be considered permissible as a primary criterion.

#     Trademark Information = [{application_info}],

#     Trademark Examination Guidelines = [{standards_trademark}]
 

#     Please fill out the trademark application in the following format.
#     등록 상태: (Must you choose between 승인 or 거절)
#     이유:
#     '''
# "Please answer without using tools."
#   Search results for "patent information search service" of "{input_brand}" = {similar_application_info},
# If there is an identical trademark by the same applicant, the application is permissible

# print(main_gpt('4020190066112', '모두웰')['output'])
# print(main_gpt('4020190081781', '한의원 무본자강 무본자강')['output'])
# print(main_gpt('4020190006385', '버드리')['output'])
# print(main_gpt('4020190095594', '다함께 차차차')['output'])
# print(main_gpt('4020190087323', '하프밀')['output'])
# print(main_gpt('4020190071086', '히비초')['output'])
# print(main_gpt('4020190070881', '별미당 별미당')['output'])
# print(main_gpt('4020197007303', '살박사은좌')['output'])
# print(main_gpt('4020190053381', '통일한의원')['output'])
# print(main_gpt('4020190086677', '태양점보히터')['output'])
# print(main_gpt('4020190052584', '문영월')['output'])
# print(main_gpt('4020190104554', '칼로바이 프로틴 에이드')['output'])
# print(main_gpt('4020190023076', '무스웰 미니컵')['output'])
# print(main_gpt('4020190015159', '당신의 피부혈액형은 무엇입니까?')['output'])
# print(main_gpt('4020190090617', '나티커')['output'])
# print(main_gpt('4020190027144', '살 빼주는 언니')['output'])
# print(main_gpt('4020190018027', '어른이놀이터')['output'])
# print(main_gpt('4020190051360', '현자의 돌 생활과 윤리')['output'])
# print(main_gpt('4020190068309', '대성자동문')['output'])
# print(main_gpt('4020190054525', '아마존펫')['output'])
# print(main_gpt('4020190099709', '메이크케어')['output'])
# print(main_gpt('4020190110347', '래쉬픽')['output'])
# print(main_gpt('4020190095000', '포모나')['output'])
# print(main_gpt('4020190102428', '패티온')['output'])
# print(main_gpt('4020190084058', '좋은 집 좋은 자재')['output'])
# print(main_gpt('4020190106613', '엑토인')['output'])
# print(main_gpt('4020190092063', '예지미인 데일리 코튼')['output'])
# print(main_gpt('4020190069854', '한국정품인증')['output'])
# print(main_gpt('4020190046577', '천연성분 편백나무 향이 그대로- 주식회사 피톤치드 수')['output'])
# print(main_gpt('4020190109038', '자연 담은 유리병')['output'])



# print("타입:", main_agent('4020190109038')['output'])