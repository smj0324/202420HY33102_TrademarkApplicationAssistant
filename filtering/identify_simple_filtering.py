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
        try:
            record = {
                'application_code': similar_application_info['application_code'][i],
                'title': similar_application_info['title'][i],
                'applicant_name': similar_application_info['applicant_name'][i],
                'similar_code': similar_application_info['similar_code'][i]
            }
        except:
            records = {}
            continue
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
            'application_number': similar_record['application_code'],
            'trademark_name': similar_record['title'],
            'applicant_name': similar_record['applicant_name'],
            'trademark_IPA_similarity': 0.0,
            'applicant_name_match': False,
            'similar_code_match': False
        }

        # Title similarity check
        record_result['trademark_IPA_similarity'] = compare_ipa_similarity(input_title, similar_record['title'])

        # Applicant name similarity check
        record_result['applicant_match'] = (input_applicant == similar_record['applicant_name'])

        # Similar class similarity check
        if [] in input_similar_codes or [] in similar_record['similar_code']:
            record_result['similar_code_match'] = False
        else:
            record_result['similar_code_match'] = is_subset(input_similar_codes, similar_record['similar_code'])
        
        results.append(record_result)
    
    return results


def is_subset(input_list, comparison_list):
    return all(item in comparison_list for item in input_list)
