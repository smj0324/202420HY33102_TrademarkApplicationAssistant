import os
import wikipediaapi
from src.worker import convert
from model.model import embedding_model
from tools.load_data import load_dict_from_json
from sklearn.metrics.pairwise import cosine_similarity
from pinecone import Pinecone


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


# 한국어 기초사전 api (한자)
# 국립 국어원 api (사전)
# 검색 api (아직 모름)