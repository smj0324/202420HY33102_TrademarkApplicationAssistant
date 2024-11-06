from custom_tools.tools import compare_ipa_similarity

def result_by_simple_test(application_info, similar_application_info):
    similar_application_info_record = convert_similar_application_info(similar_application_info)
    result = compare_records(application_info, similar_application_info_record)
    # print("단순 식별력 검사:", result)
    return result

def convert_similar_application_info(similar_application_info):
    num_records = len(similar_application_info['application_code'])
    records = []
    for i in range(num_records):
        record = {
            'application_code': similar_application_info['application_code'][i],
            'title': similar_application_info['title'][i],
            'applicant_name': similar_application_info['applicant_name'][i],
            'similar_code': similar_application_info['similar_code'][i]
        }
        records.append(record)
    return records

def compare_records(application_info, similar_records, 
                   title_threshold=80, 
                   applicant_name_threshold=80):
    """
    입력 데이터와 기존 데이터의 각 레코드를 비교하여 유사성을 체크
    
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
    input_title = application_info.get('title', '')
    input_applicant = application_info.get('applicant_name', '')
    input_similar_codes = application_info.get('similar_code', [])
    
    for similar_record in similar_records:
        record_result = {
            '출원 번호': similar_record['application_code'],
            '상표명': similar_record['title'],
            '상표의 IPA 발음 유사도 thrsehold 0.8': 0.0,
            '출원인이 같음': False,
            '유사군이 같음': False
        }
        
        # Title 유사성 체크
        record_result['상표의 IPA 발음 유사도 thrsehold 0.8'] = compare_ipa_similarity(input_title, similar_record['title'])
        
        # Applicant Name 유사성 체크
        record_result['출원인이 같음'] = (input_applicant == similar_record['applicant_name'])
        
        # Similar Code 유사성 체크
        record_result['유사군이 같음'] = is_subset(input_similar_codes, similar_record['similar_code'])
        
        results.append(record_result)
    
    return results


def is_subset(input_list, comparison_list):
    return all(item in comparison_list for item in input_list)
