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