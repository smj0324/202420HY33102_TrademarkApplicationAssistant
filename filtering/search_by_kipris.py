import os
import re
import sys
import json
# import deepl
import requests
import xmltodict
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from collections import defaultdict
from custom_tools.tools import ryu_and_similarity_code

KIPRIS_API_KEY = os.getenv('_KIPRIS_API_KEY')
# DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')
# TRANSLATOR = deepl.Translator(DEEPL_API_KEY)


class CodeSearchKipris:
    '''
    입력 상표명에 해당하는 정보 관리
    '''
    def __init__(self, application_code="", title="", single_flag=True) -> None:
        self.application_code = application_code
        self.title = title
        self.fulltitle = ""
        self.applicant_name = ""
        self.nice_code = []
        self.similar_code = []
        self.similar_code_hangle = []
        self.application_status = ""
        self.is_valid_category_match = True
        self.single_flag = single_flag

    def _search_by_code(self):
        url_general = f"http://plus.kipris.or.kr/kipo-api/kipi/trademarkInfoSearchService/getWordSearch?searchString={self.application_code if self.single_flag else self.title}&searchRecentYear=0&ServiceKey={KIPRIS_API_KEY}"
        
        response_general = requests.get(url_general)
        if response_general.status_code != 200:
            print("Failed to retrieve general data from KIPRIS API")
            return None
        
        if not response_general.text or "<title>" not in response_general.text or "정보 없음" in response_general.text:
            return None

        
        else:
            application_general_dict = parsing_application_data(response_general, self.application_code, self.single_flag)
        
        if self.single_flag:
            self.applicant_name = application_general_dict.get('applicantName', "")
            self.fulltitle = application_general_dict.get('fulltitle', "")
            self.application_status = application_general_dict.get('applicationStatus', "")
        else:
            self.application_code = [item.get('applicationNumber', "") for item in application_general_dict]
            self.applicant_name = [item.get('applicantName', "") for item in application_general_dict]
            self.title = [item.get('title', "") for item in application_general_dict]
            self.application_status = [item.get('applicationStatus', "") for item in application_general_dict]


    def _search_by_application_code(self):

        if self.single_flag:
            url_similar = f"http://plus.kipris.or.kr/openapi/rest/trademarkInfoSearchService/trademarkDesignationGoodstInfo?applicationNumber={self.application_code}&accessKey={KIPRIS_API_KEY}"
            
            response_similar = requests.get(url_similar)
            if response_similar.status_code != 200:
                print("Failed to retrieve similar group data from KIPRIS API")
                return None
            
            classification_codes_list, similar_group_codes_list, similar_group_hangle_list = parsing_nice_code(response_similar)
            self.nice_code = classification_codes_list
            self.similar_code = similar_group_codes_list
            self.similar_code_hangle = similar_group_hangle_list
            
            self.is_valid_category_match = ryu_and_similarity_code(self.nice_code, self.similar_code)
            
        else:
            all_nice_codes = []
            all_similar_codes = []
            all_similar_hangle = []

            for target_code in self.application_code:
                url_similar = f"http://plus.kipris.or.kr/openapi/rest/trademarkInfoSearchService/trademarkDesignationGoodstInfo?applicationNumber={target_code}&accessKey={KIPRIS_API_KEY}"
                
                response_similar = requests.get(url_similar)

                if response_similar.status_code != 200:
                    print(f"Failed to retrieve similar group data for application number {target_code} from KIPRIS API")
                    continue
                
                if not response_similar.text or ("<SimilargroupCode>" not in response_similar.text):
                    return None
                
                else:
                    classification_codes_list, similar_group_codes_list, similar_group_hangle_list = parsing_nice_code(response_similar)
                    all_nice_codes.append(classification_codes_list)
                    all_similar_codes.append(similar_group_codes_list)
                    all_similar_hangle.append(similar_group_hangle_list)

            self.nice_code = all_nice_codes
            self.similar_code = all_similar_codes
            self.similar_code_hangle = all_similar_hangle


    def to_dict(self) -> dict:
        """
        객체의 상태를 딕셔너리 형태로 변환하여 반환.

        Returns:
            dict: 객체의 모든 속성과 그 값을 포함한 딕셔너리.
        """
        return {
            "application_code": self.application_code,
            "title": self.title,
            "fulltitle": self.fulltitle,
            "applicant_name": self.applicant_name,
            "application_status": self.application_status,
            "nice_code": self.nice_code,
            "similar_code": self.similar_code,
            "similar_code_name": self.similar_code_hangle,
            "is_valid_category_match": self.is_valid_category_match
        }

    # def save_to_dict_attribute(self):
    #     """
    #     객체의 상태를 딕셔너리 형태로 내부 속성에 저장.
    #     """
    #     self.state_dict = self.to_dict()


def parsing_application_data(response_general, application_code, single=True):
    # print("\n\n\n\n\n****************",response_general.text)
    dict_general = xml_to_dict(response_general)
    items = dict_general.get('response', {}).get('body', {}).get('items', {}).get('item', [])

    if isinstance(items, dict):
        items = [items]
    elif not isinstance(items, list):
        items = []

    if single:
        # 단일 데이터 처리
        parsed_data = next((item for item in items if item['applicationNumber'] == application_code), None)
        if parsed_data:
            return {
                'applicationStatus': parsed_data['applicationStatus'],
                'title': parsed_data['title'],
                'applicantName': parsed_data['applicantName'],
            }
        else:
            print("해당 applicationNumber에 대한 정보가 없습니다.")
            return {}
    
    extracted_info = []

    for item in items:
        application_status = item.get('applicationStatus', "")
        application_date = item.get('applicationDate', "")

        # 조건에 맞는 데이터만 저장
        if application_status == "등록" and application_date and int(application_date[:4]) < 2019:
            data = {
                'applicationNumber': item['applicationNumber'],
                'applicationStatus': application_status,
                'title': item['title'],
                'applicantName': item['applicantName'],
                'applicationDate': application_date,
            }
            extracted_info.append(data)

    return extracted_info


def parsing_nice_code(response_similar):
    # print("*****************,",response_similar.text)
    dict_similar = xml_to_dict(response_similar)
    # print("***************\n")
    response = dict_similar.get('response')
    
    if response is None:
        print("Warning: 'response'가 None입니다.")
        return [], [], []

    body = response.get('body')
    if body is None:
        print("Warning: 'body'가 None입니다.")
        return [], [], []

    items = body.get('items')
    if items is None:
        print("Warning: 'items'가 None입니다.")
        return [], [], []
    
    trademark_info = items.get('trademarkDesignationGoodstInfo', [])
    if isinstance(trademark_info, dict):
        trademark_info = [trademark_info]

    grouped_data = defaultdict(list)

    classification_codes = set()
    en_names = set()
    # print(f"Initial type of trademark_info: {type(trademark_info)}")
    for item in trademark_info:
        # print(f"Initial type of item: {type(trademark_info)}")
        try:
            classification_code = int(item.get('DesignationGoodsClassificationInformationCode', 0))
            similargroup_code = item.get('SimilargroupCode', "")
            en_name = item.get('DesignationGoodsHangeulName', "")

            if classification_code and similargroup_code and en_name:
                classification_codes.add(classification_code)
                en_names.add(en_name)
                grouped_data[en_name].append(similargroup_code)
        except (ValueError, KeyError) as e:
            print(f"데이터 항목에서 오류 발생: {e}")
            continue

    classification_codes_list = [str(code) for code in classification_codes]
    similar_group_codes_list = list(grouped_data.values())

    unique_similar_group_codes_set = {
        ",".join(sorted(x)) if len(x) > 1 else x[0] 
        for x in set(tuple(codes) for codes in similar_group_codes_list)
    }
    unique_similar_group_codes_list = list(unique_similar_group_codes_set)
    en_names_list = list(en_names)

    return classification_codes_list, unique_similar_group_codes_list, en_names_list



def xml_to_dict(response):
    try:
        return xmltodict.parse(response.content)
    
    except Exception as e:
        print(f"Error parsing XML response: {e}")
        return {}


#단일 application_code 테스트
# print("===== 단일 application_code 테스트 =====")
# single_code_test = CodeSearchKipris(application_code="4020190099709", single_flag=True)
# single_code_test._search_by_code()
# single_code_test._search_by_application_code()
# print(json.dumps(single_code_test.to_dict(), ensure_ascii=False, indent=4))

# print("단일 상표명 검색 결과:")
# print(f"신청자 이름: {single_code_test.applicant_name}")
# print(f"제목: {single_code_test.title}")
# print(f"상태: {single_code_test.application_status}")
# print(f"니스 코드: {single_code_test.nice_code}")
# print(f"유사 코드: {single_code_test.similar_code}")
# print(f"유사 코드 한국어: {single_code_test.similar_code_hangle}")
# print(f"류 유사군 mapping: {single_code_test.is_valid_category_match}")

# print(ryu_and_similarity_code(single_code_test.nice_code, single_code_test.similar_code))
# print(ryu_and_similarity_code("3", ["G1201", "S120907", "S128302"]))
 
# url = f"http://plus.kipris.or.kr/openapi/rest/trademarkInfoSearchService/trademarkVfersionInfo?applicationNumber=4020190099709&accessKey={KIPRIS_API_KEY}"
# response_similar = requests.get(url)
# print(xmltodict.parse(response_similar.content))

# url = f"http://plus.kipris.or.kr/openapi/rest/trademarkInfoSearchService/trademarkSimilarCodeSearchInfo?similarCode=G1301,G1201&accessKey={KIPRIS_API_KEY}"
# response_similar = requests.get(url)
# print(xmltodict.parse(response_similar.content))
# # 여러 application_code 테스트
# print("\n===== 여러 application_code 테스트 =====")
# multi_code_test = CodeSearchKipris(title="하프밀  -", single_flag=False)
# multi_code_test._search_by_code()
# multi_code_test._search_by_application_code()

# print("여러 상표명 검색 결과:")
# print(f"신청자 이름 리스트: {multi_code_test.applicant_name}")
# print(f"제목 리스트: {multi_code_test.title}")
# print(f"상태 리스트: {multi_code_test.application_status}")
# print(f"니스 코드 리스트: {multi_code_test.nice_code}")
# print(f"유사 코드 리스트: {multi_code_test.similar_code}")
# print(f"유사 코드 한국어: {multi_code_test.similar_code_hangle}")


# print(json.dumps(multi_code_test.to_dict(), ensure_ascii=False, indent=4))
# en_name = TRANSLATOR.translate_text("모두웰"+"'", target_lang="EN-US").text
# print(en_name)