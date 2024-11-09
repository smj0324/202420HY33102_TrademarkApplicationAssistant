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
    print("\n\n\n\n\nsimilar_application_info:",similar_application_info)

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
        # reason_text = extract_reason(each_result) 
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
        
        - Guidelines:
            1. If a highly similar trademark is already registered by the same applicant, this application must be approved without exception. In such cases, ignore any other considerations—this trademark must be approved.
            2. Check similarity based only on the trademark name, not the applicant.
            3. If the Simliar code is false, the designated product is different, so there is still a review standard to consider. Therefore, please write down the approval for now.

        2. Output Format
        Predict Status: choice approve or reject
        Reason: [Do not state whether the application is approved or rejected in the rationale. Only mention approval if the applicant is the same as an existing registered trademark.]
        """


    elif code == 2:
        template = f"""
            Here’s a refined version that emphasizes the need for detailed and precise reasoning:

            Please evaluate the trademark registration eligibility of "{title}" based on the following criteria and provide a response with specific and accurate reasoning grounded in the trademark examination standards.

            If any related precedents are applicable, please reference them and provide a detailed explanation based on those precedents. [{sample}]
            Please use the following format for your response:

            Positive Reason: [Provide specific and accurate reasons, based on applicable standards, why this trademark may be approved.]

            Negative Reason: [Provide specific and accurate reasons, grounded in examination standards, why this trademark may not be approved.]
        """

    elif code == 3:
        template = f"""
        Please verify the trademark registration eligibility of "{title}" according to the Trademark Examination Guidelines.

        Trademark Examination Guidelines:
        - The guidelines are broad, so please review them by table of contents for a thorough review of each section..
        - Assess whether "{title}" meets the criteria by considering the unique impression it may create for the relevant goods or services, particularly in the market where it will be applied.

        **Trademark Examination Standards**: [{standards_trademark}]

        **Output Format**:
        Positive Reason: [Provide specific and accurate reasons, based on applicable standards, why this trademark may be approved.]
        Negative Reason: [Provide specific and accurate reasons, grounded in examination standards, why this trademark may not be approved.]
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



sample = """
Chapter 2 Requirements for Trademark Registration

<Law, Article 6, Paragraph 1, Item 1>

A trademark that solely consists of marks generally used as common names for the relevant goods.

Article 6 (Trademarks for Common Names of Goods)

According to Item 1 of Article 6, Paragraph 1 of the Law (hereinafter referred to as "this Item"), the term "common name of the goods" includes abbreviated names, colloquial names, or other names commonly used in the trade society (consisting of general consumers and industry professionals) to refer to the goods in question.

Even if a trademark contains a common name as defined in Paragraph 1, if it is displayed in a unique manner, or if the common name is used only as an additional detail and is not a primary component of the trademark, allowing it to be distinctive, then this Item does not apply.

When distinctiveness is recognized due to the circumstances described in Paragraph 2, if there is a risk of confusion or misunderstanding about the designated goods, the scope of the designated goods may be limited to those related to the common name as per Article 7, Paragraph 1, Item 11 of the Law.

Reference Materials for Interpretation:

The common name referred to in this Item means a name that is actually used and recognized by the trade society (including general consumers and the industry) to identify the goods in question. However, for a name to be considered a common name, it is not enough for the general consumer to merely perceive it as such; the name must be genuinely used in the trade as a general name for the specific goods.
Examples of Designated Goods and Trademarks:

Automobile: CAR
Car bulbs: Truck Lite
Clothing: Jeans
Packaging film: Wrap
Corn snacks: Corn Chips
Walnut-based cookies: Walnut Cookie
Copying machine: Copier
Plastic laminated sheets for furniture: Formica
Stomach medicine containing Greosote: Jeongro-hwan
Fermented milk: YOGURT
Foundation cream: Foundation
Advertising services: Radio Advertising, Television Advertising
Communication services: Computer Communication, Telephone Communication
Insurance services: Life Insurance, Auto Insurance
Restaurant services: Restaurant, Cafe, Grill
For unregistered varieties under the Seed Industry Act, if a trademark identical to the name of a widely known variety of agricultural products is registered for seeds or similar products, this Item applies, and if the trademark indicates the nature of the goods, Item 3 of Article 6, Paragraph 1 will also apply.
Law, Article 6, Paragraph 1, Item 2

A trademark that is commonly used for the goods in question.

Article 7 (Commonly Used Trademarks)

According to Item 2 of Article 6, Paragraph 1 of the Law (hereinafter referred to as "this Item"), "commonly used trademark" refers to marks that have been commonly used among competitors to such an extent that they no longer serve as an indication of the source of goods.

However, if a commonly used mark is used as an additional detail rather than a major part of the trademark, and other parts provide distinctiveness, this Item does not apply.

Reference Materials for Interpretation:

To be a commonly used trademark, it must meet the following requirements:
The trademark is generally used by various unspecified individuals, such as manufacturers or sellers, for specific goods.
As a result, the trademark has lost its source-indicating function or distinctiveness.
The trademark owner has not taken necessary measures to protect the trademark.
Examples of Commonly Used Trademarks and Designated Goods:

Sake: Seishu
Cognac: Napoleon
Cold lozenges: In-dan
Fabric: TEX, LON, RAN
Decorative sheets: Deco Sheet
Snacks: Crackers
Cold cream: Vaseline
Communication services: Cyber, Web, Tel, Com, Net
Hospitality: Tourist Hotel, Park
Restaurant services: Garden, Pavilion, Hall
Law, Article 6, Paragraph 1, Item 3

A trademark that solely consists of marks indicating the origin, quality, material, effectiveness, use, quantity, shape (including packaging shape), price, production method, processing method, usage, or timing of the goods.

Article 8 (Descriptive Trademarks)

A "mark indicating origin" under Item 3 of Article 6, Paragraph 1 of the Law (hereinafter referred to as "this Item") refers to a place that enables consumers to directly perceive the characteristics of the goods due to the geographical conditions of the region. The mark applies even if the goods were historically or currently produced in that area, or if consumers generally associate the goods with that location.

A "mark indicating quality" refers to a mark directly representing the quality or superiority of the designated goods.

A "mark indicating material" refers to a mark that represents a primary or secondary component actually or potentially used in the designated goods.

A "mark indicating effectiveness" represents the performance or effect of the goods.

A "mark indicating use" represents the use or purpose of the designated goods.

A "mark indicating quantity" refers to a mark commonly recognized in trade to represent the quantity, unit, and symbol of the designated goods.

A "mark indicating shape or packaging shape" represents the external appearance, form, pattern, or specifications of the goods.

A "mark indicating price" represents the price and price indication units generally recognized in trade.

A "mark indicating production, processing, or usage method" refers to marks that directly represent how the designated goods are produced, processed, or used.

A "mark indicating timing" represents the season, time, or period of sale or use for the goods.

Examples of Descriptive Marks and Designated Goods:

Ginseng: Geumsan
Apples: Daegu
Dried fish: Yeonggwang
Fabrics: Hansan
Squid: Ulleungdo
Glasses: VIENNA
Korean cuisine management (hangover soup): Cheongjindong
Simple dining services (buckwheat noodles, spicy grilled chicken): Chuncheon
Korean cuisine management (spicy fish stew): Masan
Restaurant services (grilled ribs): Idong
Tea: Pu’er (茶)
If indicating the origin (including sales location) enhances the value or reputation of the goods, and there is a risk of misrepresentation or confusion when goods produced or sold outside of the designated origin bear that origin’s name, Article 7, Paragraph 1, Item 11 of the Law applies.

Quality indications as defined in Paragraph 2 may include indicators of grade, quality assurance, aesthetic qualities, or even the reputation of the product. The actual quality may not be relevant, but if the indicated quality is absent or exaggerated, Article 7, Paragraph 1, Item 11 of the Law also applies.

Examples of Quality Indications and Designated Goods:

All goods: Superior, Standard, Pure, Original, Genuine, Deluxe, New, Complete, First-class, Specialty, Excellent, KS, JIS
Environment-related goods: Clean, Eco-friendly, GREEN, BIO
Cosmetics: Soft Brown
Green tea: Vitality water
Undershirts: High-running
Clothing: ELEGANCE BOUTIQUE, SHEER ELEGANCE
Technology-related products: Hitec
Hospitality: TRAVEL LODGE
Raw materials as defined in Paragraph 3 include primary and secondary components that significantly affect the goods’ quality or performance. Even if the component is not widely used but could potentially be used, and its inclusion causes misrepresentation or confusion, Article 7, Paragraph 1, Item 11 of the Law applies.
Examples of Raw Material Indications and Designated Goods:

Tofu: Soybeans
Suits: WOOL
Window frames: Aluminum
Safes: STEEL
Blouses: SILK
Cosmetics, soaps, etc.: KERATIN
Performance indications under Paragraph 4 include not only objective qualities of the product but also subjective qualities like comfort or satisfaction. The actual existence of these properties is irrelevant; Article 7, Paragraph 1, Item 11 also applies if the representation is absent or misleading.
Examples of Performance Indications and Designated Goods:

Medicine: Effective
Tea: Vitality water
Cosmetics: Smooth
Furniture: Elegant
Microwave: One-touch
Copier: Quick copy
Eyeliner, mascara: Decoration Eyes
Communication software, computers: Efficient Network
Paints, dyes: Glass Deco
Lipstick, nail polish: Color Wearing
Use indications under Paragraph 5 represent purposes such as application areas, target consumer groups, versatility, or leisure-oriented functions.
Examples of Use Indications and Designated Goods:

Fertilizer: Gardening
Cola: DIET COLA
Soccer shoes: KICKERS
Bags: Student
Clothing: Baby
Sports equipment: Professional
Books: Market Report
Cosmetics:
Additional Notes:

For combinations of technical (descriptive) marks related to goods, if they convey characteristics in a way that the general public would recognize as descriptive, then Item 3 of Article 6, Paragraph 1 applies.

For trademarks indicating qualities that may mislead or deceive consumers regarding the nature or characteristics of goods, Article 7, Paragraph 1, Item 11 applies.

"""