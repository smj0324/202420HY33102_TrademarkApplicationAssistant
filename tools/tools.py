import os
import wikipediaapi
import requests
import xml.etree.ElementTree as ET
from src.worker import convert
from model.model import embedding_model
from tools.load_data import load_dict_from_json
from sklearn.metrics.pairwise import cosine_similarity
from pinecone import Pinecone


KOREAN_API = os.getenv('KOREAN_API')
BASIC_KOREAN_API = os.getenv('BASIC_KOREAN_API')

PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("heymin")

nice_to_similar = load_dict_from_json()


def similarity(a, b):
    return cosine_similarity([a], [b])[0][0]


def calculate_similarity(target, comparison_list):
    cal_similar_list = []
    embedd_target = embedding_model.embed_documents(target)
    embedd_comp_list = embedding_model.embed_documents(comparison_list)
    
    for i, emb in enumerate(embedd_comp_list, start=2):
      sim = similarity(embedd_target, emb)
      cal_similar_list.append(sim)

    return cal_similar_list


def search_law_by_pdf(query):
    embedded_sentences = embedding_model.embed_documents(query)

    law_search_results = index.query(
        vector=embedded_sentences[0],
        top_k=3,
        include_values=False,
        include_metadata=True
    )

    return law_search_results


def convert_ipa(word):
    try:
        ipa_output = convert(word)
        return ipa_output
    except Exception as e:
        print(f"Error converting text: {e}")
        return None


def ryu_and_similarity_code(nice_code, similar_code):
    '''
    Parameter:
        nice_code: 단일 int 값
        similarity_code: 단일 값이 아닌 여러 값이 포함된 리스트 형식 일 수 있음
    '''

    if nice_code not in nice_to_similar:
        return False
    
    return similar_code in nice_to_similar[nice_code]


def serch_by_wikipidia(brand):
    wiki_wiki = wikipediaapi.Wikipedia('MyProject/1.0 (das@naver.com)', 'ko', extract_format=wikipediaapi.ExtractFormat.WIKI)
    page_py = wiki_wiki.page(brand)
    wiki_content = page_py.summary[0:300]

    return page_py.exists(), wiki_content


def search_chinese_character(query):
    '''
    TODO: 반환형식 통일 및 PRINT문 삭제
    '''
    url = f"https://krdict.korean.go.kr/api/search?key={BASIC_KOREAN_API}&q={query}&advanced=y&trans_lang=2"

    response = requests.get(url)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        hanja_words = []

        for item in root.findall('.//item'):

            origin = item.find('origin').text if item.find('origin') is not None else '정보 없음'  # origin 추가
            
            if origin != '정보 없음':
                hanja_words.append(origin)

        print("\n한자어 리스트:")
        print(", ".join(hanja_words) if hanja_words else '없음')

    else:
        print(f"Error: {response.status_code}")

    return hanja_words


def search_korean_character(query):
    '''
    TODO: 반환형식 통일 및 PRINT문 삭제
    '''
    url = f"https://stdict.korean.go.kr/api/search.do?key={KOREAN_API}&q={query}&advanced=y&type2=all"

    response = requests.get(url)

    if response.status_code == 200:
        root = ET.fromstring(response.text)
        items = root.findall(".//item")

        if not items:  # 검색 결과가 없을 때
            print("결과가 없습니다.")
        else:
            for item in items:
                word = item.find("word").text
                if word == query:
                    definition = item.find(".//definition").text

                    print(f"Word: {word}")
                    print(f"Definition: {definition}")
                    print("-" * 40)
    else:
        print(f"Error: {response.status_code}")


def search_by_query(query):
    ...