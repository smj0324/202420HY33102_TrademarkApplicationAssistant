import os
import sys
import requests
import wikipediaapi
import xml.etree.ElementTree as ET

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from custom_tools.src.worker import convert
from model.model import embedding_model
from custom_tools.load_data import load_nice_dict_from_json
from sklearn.metrics.pairwise import cosine_similarity
from pinecone import Pinecone
from langchain.tools import tool

KOREAN_API = os.getenv('KOREAN_API')
BASIC_KOREAN_API = os.getenv('BASIC_KOREAN_API')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
GOOGLE_SEARCH_KEY = os.getenv('GOOGLE_SEARCH_KEY')
GOOGLE_ID = os.getenv('GOOGLE_ID')

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("heymin")

nice_to_similar = load_nice_dict_from_json()
embeddings = embedding_model()

wiki_wiki = wikipediaapi.Wikipedia('MyProject/1.0 (das@naver.com)', 'ko', extract_format=wikipediaapi.ExtractFormat.WIKI)


def ryu_and_similarity_code(nice_codes, similar_codes):
    for nice_code in nice_codes:
        if nice_code in nice_to_similar:
            mapped_similar_codes = nice_to_similar.get(nice_code, [])
            
            for code in similar_codes:
                if code not in mapped_similar_codes:
                    return False
                
    return True


def asigned_tools():
    tools = [
        search_by_wiki, 
        search_chinese_character, 
        search_korean_character,
        google_search
        ]
    
    return tools


@tool
def search_by_wiki(query):
    """Search Wikipedia for a given query and return a summary of the page."""

    page_py = wiki_wiki.page(query)
    
    if page_py.exists():
        return page_py.summary[0:1000]
    else:
        return "No good Wikipedia Search Result was found"


def similarity(a, b):
    """Calculate the cosine similarity between two vectors."""
    
    return cosine_similarity([a], [b])[0][0]


def calculate_similarity(target, comparison_list):
    """A tool used to identify similar trademarks.Returns each similarity list of list elements given a list with input and comparison words."""
    
    cal_similar_list = []
    embedd_target = embeddings.embed_documents(target)
    embedd_comp_list = embeddings.embed_documents(comparison_list)
    
    for i, emb in enumerate(embedd_comp_list, start=2):
      sim = similarity(embedd_target, emb)
      cal_similar_list.append(sim)

    return cal_similar_list


def search_law_by_pdf(query):
    """Search for laws related to the query by analyzing about Trademark precedent PDF documents and return the top 3 results. An example of a query is "저명한 명칭인 경우와 관련된 판례"."""
    
    embedded_sentences = embeddings.embed_documents(query)

    law_search_results = index.query(
        vector=embedded_sentences[0],
        top_k=3,
        include_values=False,
        include_metadata=True
    )

    return law_search_results


def convert_ipa(word):
    """Convert a given word to its International Phonetic Alphabet (IPA) representation."""
    
    try:
        ipa_output = convert(word)
        return ipa_output
    except Exception as e:
        print(f"Error converting text: {e}")
        return None
    

def compare_ipa_similarity(word1: str, word2: str) -> float:
    """As a tool for pronunciation similarity testing, we convert two words into International Phonetic Symbols (IPAs) and then calculate the similarity of their IPA expressions."""
    try:
        ipa1 = convert_ipa(word1)
        if ipa1 is None:
            print(f"Error: Failed to convert ipa for '{word1}'")
            return None

        ipa2 = convert_ipa(word2)
        if ipa2 is None:
            print(f"Error: Failed to convert ipa for '{word2}'")
            return None

        embedd_ipa1 = embeddings.embed_documents([ipa1])[0]
        embedd_ipa2 = embeddings.embed_documents([ipa2])[0]

        sim_score = similarity(embedd_ipa1, embedd_ipa2)

        return sim_score

    except Exception as e:
        print(f"Error in compare_ipa_similarity: {e}")
        return None


@tool
def search_chinese_character(query):
    """Search for Chinese characters (Hanja) corresponding to the Korean query using the Korean dictionary API."""
    
    url = f"https://krdict.korean.go.kr/api/search?key={BASIC_KOREAN_API}&q={query}&advanced=y&trans_lang=2"

    response = requests.get(url)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        hanja_words = []

        for item in root.findall('.//item'):

            origin = item.find('origin').text if item.find('origin') is not None else '정보 없음'  # origin 추가
            
            if origin != '정보 없음':
                hanja_words.append(origin)
    else:
        print(f"Error: {response.status_code}")

    return hanja_words


@tool
def search_korean_character(query):
    """Search for Korean characters and their definitions using the standard Korean dictionary API."""

    url = f"https://stdict.korean.go.kr/api/search.do?key={KOREAN_API}&q={query}&advanced=y&type2=all"

    response = requests.get(url)

    if response.status_code == 200:
        root = ET.fromstring(response.text)
        hangle_words = []
        hangle_definitions = []

        items = root.findall(".//item")

        if not items:
            return "Korean dictionary Search Result was not found"
        
        else:
            for item in items:
                word = item.find("word").text
                if word == query:
                    definition = item.find(".//definition").text

                    hangle_words.append(word)
                    hangle_definitions.append(definition)
    else:
        print(f"Error: {response.status_code}")

    return {
        "word": hangle_words,
        "definitions": hangle_definitions
    }


@tool
def google_search(query:str) -> list:
    """It can be used to search for news or blogs about the brand name, returning 3 titles and a little description of the Google search results."""
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': GOOGLE_SEARCH_KEY,
        'cx': GOOGLE_ID,
        'q': query,
        'num': 3  # top -k 3
    }

    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        try:
            items = response.json().get('items', [])
            print(items)
            google_search_list = [{"title": item.get("title", ""), "description": item.get("snippet", "")} for item in items]
            return google_search_list
        except ValueError:
            print("Error: JSON decoding fail")
            return []
    else:
        print(f"Error: {response.status_code}")
        print("Response Body:", response.text)
        return []