import os

KIPRIS_API_KEY = os.getenv('KIPRIS_API_KEY')

class BrandSearchKipris:
    '''
    입력 상표명에 해당하는 정보 관리
    '''
    def __init__(self) -> None:
        self.application_code = ""
        self.brand = ""
        self.applicant_name = ""
        self.nice_code = ""
        self.similar_code = ""

    def search_by_brand(brand):
        ...
    def search_by_application_code(appli_code):
        ...