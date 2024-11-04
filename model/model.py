import os

from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv(verbose=True)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def embedding_model(model="text-embedding-3-small"):
    embeddings = OpenAIEmbeddings(model=model, api_key = OPENAI_API_KEY)
    return embeddings
