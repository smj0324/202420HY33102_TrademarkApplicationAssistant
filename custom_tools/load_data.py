import os
import json

def load_nice_dict_from_json(json_file='.\custom_tools\data\sorted_output.json'):
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
    

def load_json_law_guidelines(json_file='.\custom_tools\data\eng_law_text.json'):
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
            guidelines_json = json.dumps(data, ensure_ascii=False, indent=4) 

    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {json_file}")

    except json.JSONDecodeError as e:
        print(f"JSON 디코딩 오류: {e}")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")

    return guidelines_json


def read_text_file(file_path='.\custom_tools\data\eng_law_text.txt'):
    # 파일을 읽고 내용을 반환
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        
    return content