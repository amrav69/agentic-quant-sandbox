import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_gemini_client(model='gemini-2.0-flash-exp'):
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=os.getenv('GEMINI_API_KEY'),
        temperature=0.7
    )

def get_groq_client(model='llama-3.3-70b-versatile'):
    return ChatOpenAI(
        model=model,
        api_key=os.getenv('GROQ_API_KEY'),
        base_url='https://api.groq.com/openai/v1',
        temperature=0.7
    )

def get_openai_client(model='gpt-4o'):
    return ChatOpenAI(
        model=model,
        api_key=os.getenv('OPENAI_API_KEY'),
        temperature=0.7
    )
