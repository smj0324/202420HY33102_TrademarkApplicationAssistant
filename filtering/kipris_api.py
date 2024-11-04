import os
import re
import requests

KIPRIS_API_KEY = os.getenv('KIPRIS_API_KEY')

class BrandSearchKipris:
    '''
    입력 상표명에 해당하는 정보 관리
    '''
    def __init__(self, application_code, brand) -> None:
        self.application_code = application_code
        self.brand = brand
        self.applicant_name = ""
        self.nice_code = ""
        self.similar_code = ""

    def search_by_brand(self):
        url_general = f"""
                        http://plus.kipris.or.kr/kipo-api/kipi/trademarkInfoSearchService
                        /getWordSearch?searchString={self.application_code}
                        &searchRecentYear=0&ServiceKey={KIPRIS_API_KEY}"""
        
        response_general = requests.get(url_general)
        if response_general.status_code != 200:
            print("Failed to retrieve general data from KIPRIS API")
            return None
        

    def search_by_application_code(self):
        url_similar = f"""
                        http://plus.kipris.or.kr/openapi/rest/trademarkInfoSearchService
                        /trademarkDesignationGoodstInfo?applicationNumber={self.application_code}
                        &accessKey={KIPRIS_API_KEY}"""
        
        response_similar = requests.get(url_similar)
        if response_similar.status_code != 200:
            print("Failed to retrieve similar group data from KIPRIS API")
            return None


def parsing_application_data(response_general):
    # TODO: application_code로 search하는데, application_code랑 똑같은 걸 찾는 과정이 필요한지 확인
    
    """_summary_

    Returns:
        _type_: _description_
    """
    try:
        dict_general = xmltodict.parse(response_general.content)
    except Exception as e:
        print(f"Error parsing general XML response: {e}")
        return None

    items = dict_general.get('response', {}).get('body', {}).get('items', {}).get('item', [])
    if not isinstance(items, list):
        items = [items] 

    item = next((i for i in items if i.get('applicationNumber') == applicationNumber), None)
    if item is None:
        print("No matching application number found.")
        return None

    applicant_name = item.get('applicantName', 'N/A')
    application_number = item.get('applicationNumber', 'N/A')
    legal_status = item.get('applicationStatus', 'N/A')
    product_name = item.get('title', 'N/A')
    product_name = re.sub(r'[A-Za-z]', '', product_name).strip()   #영어 빼기
    ...


def parsing_nice_code(response_similar):
    try:
        root = ET.fromstring(response_similar.content)
    except ET.ParseError as e:
        print(f"Error parsing similar group XML response: {e}")
        return None

    nice_codes = []
    similarity_codes = []

    def extract_codes(element):
        if element.tag.endswith("SimilargroupCode") and element.text:
            similarity_codes.append(element.text)
        elif element.tag.endswith("DesignationGoodsClassificationInformationCode") and element.text:
            nice_codes.append(element.text)
        for child in element:
            extract_codes(child)

    # XML 요소를 탐색하여 코드 추출
    extract_codes(root)
    ...