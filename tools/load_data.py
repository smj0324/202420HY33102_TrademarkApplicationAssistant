import os
import json

def load_dict_from_json(json_file='nice_to_similar.json'):
    if not os.path.exists(json_file):
            print(f"JSON 파일을 찾을 수 없습니다: {json_file}")
            return {}
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            nice_to_similar = json.load(f)
        print(f"JSON 파일을 성공적으로 불러왔습니다: {json_file}")
        return nice_to_similar
    
    except json.JSONDecodeError:
        print(f"JSON 파일을 읽는 중 오류 발생: {json_file}은 유효한 JSON 파일이 아닙니다.")
        return {}
    
    except Exception as e:
        print(f"JSON 파일을 읽는 중 오류 발생: {e}")
        return {}