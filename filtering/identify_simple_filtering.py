from custom_tools.tools import ryu_and_similarity_code

def result_by_simple_test(application_info, similar_application_info):
    # TODO: 류에 해당하는 적절한 유사군을 적지않음 RETURN; 무조건 특허등록 거절
    _self_code_result = ryu_and_similarity_code(application_info.nice_code, application_info.similar_code)
    if not _self_code_result:
        # 적절하지 않을 경우 처리
        ...

    # TODO: 검색한 상표 중에 동일한 출원인이 존재하는지 RETURN; INFO 제공
    
    # TODO: 검색한 상표명에 유사도를 같이 정보로 전달 RETURN; INFO 제공
    ...

def convert_similar_application_info(similar_application_info):
    num_records = len(similar_application_info['application_code'])
    records = []
    for i in range(num_records):
        record = {
            'application_code': similar_application_info['application_code'][i],
            'title': similar_application_info['title'][i],
            'single_flag': similar_application_info['single_flag'],
            'applicant_name': similar_application_info['applicant_name'][i],
            'similar_code': similar_application_info['similar_code'][i]
        }
        records.append(record)
    return records

def compare_records(input_record, main_records, 
                   title_threshold=80, 
                   applicant_name_threshold=80):
    """
    입력 데이터와 기존 데이터의 각 레코드를 비교하여 유사성을 체크합니다.
    
    Parameters:
    - input_record (dict): 입력 데이터 레코드
    - main_records (list of dicts): 기존 데이터 레코드 리스트
    - title_threshold (int): title 유사도 임계값
    - applicant_name_threshold (int): applicant_name 유사도 임계값
    
    Returns:
    - list of dicts: 각 레코드에 대한 유사성 체크 결과
        예: [
                {
                    'application_code': '4520160002952',
                    'title_similar': True,
                    'applicant_name_similar': True,
                    'nice_code_similar': False,
                    'similar_code_similar': False
                },
                ...
             ]
    """
    results = []
    input_title = input_record.get('title', '')
    input_applicant = input_record.get('applicant_name', '')
    input_similar_codes = input_record.get('similar_code', [])
    
    for main_record in main_records:
        record_result = {
            'application_code': main_record['application_code'],
            'title': main_record['title'],
            'title_similar': False,
            'applicant_name_similar': False,
            'similar_code_similar': False
        }
        
        # Title 유사성 체크
        record_result['title_similar'] = check_title_similarity(
            input_title, main_record['title'], title_threshold)
        
        # Applicant Name 유사성 체크
        record_result['applicant_name_similar'] = check_applicant_name_similarity(
            input_applicant, main_record['applicant_name'], applicant_name_threshold)
        
        # Similar Code 유사성 체크
        record_result['similar_code_similar'] = check_similar_code_similarity(
            input_similar_codes, main_record['similar_code'])
        
        results.append(record_result)
    
    return results