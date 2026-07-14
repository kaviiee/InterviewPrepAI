import os
import shutil

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader
)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv


load_dotenv()


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


llm = ChatOpenAI(
    model="google/gemini-2.5-flash",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0,
    streaming=True
)



splitter = RecursiveCharacterTextSplitter(
    chunk_size=1800,
    chunk_overlap=400
)



# session storage

user_documents = {}
user_db = {}
user_retriever = {}



def load_document(path):

    if path.endswith(".pdf"):
        loader = PyPDFLoader(path)

    else:
        loader = TextLoader(
            path,
            encoding="utf-8"
        )

    return loader.load()



def build_vector_db(session_id):

    docs = []


    # files = user_documents.get(
    #     session_id,
    #     []
    # )

    documents = user_documents.get(session_id, {})

    files = [
        path 
        for path in documents.values()
        if path is not None
    ]

    for file in files:

        loaded = load_document(file)


        for doc in loaded:
            doc.metadata["source"] = file


        docs.extend(loaded)



    chunks = splitter.split_documents(
        docs
    )


    db = FAISS.from_documents(
        chunks,
        embeddings
    )


    return db





# def add_document(session_id, file_path):

#     if session_id not in user_documents:
#         user_documents[session_id] = []


#     user_documents[session_id].append(
#         file_path
#     )


#     # rebuild vector database

#     user_db[session_id] = build_vector_db(
#         session_id
#     )


#     user_retriever[session_id] = (
#         user_db[session_id]
#         .as_retriever(
#             search_type="mmr",
#             search_kwargs={
#                 "k":8,
#                 "fetch_k":30
#             }
#         )
#     )

def add_document(session_id, file_path, document_type):

    if session_id not in user_documents:
        user_documents[session_id] = {
            "resume": None,
            "job": None
        }


    user_documents[session_id][document_type] = file_path


    user_db[session_id] = build_vector_db(session_id)


    user_retriever[session_id] = (
        user_db[session_id]
        .as_retriever(
            search_type="mmr",
            search_kwargs={
                "k":10,
                "fetch_k":30
            }
        )
    )



def reset_session(session_id):

    user_documents.pop(
        session_id,
        None
    )

    user_db.pop(
        session_id,
        None
    )

    user_retriever.pop(
        session_id,
        None
    )





def get_retriever(session_id):

    return user_retriever.get(
        session_id
    )


def stream_llm(query, session_id, history):

    retriever = get_retriever(session_id)

    if retriever is None:
        yield "Please upload your resume and job description first."
        return

    docs = retriever.invoke(query)

    context = "\n\n".join(
        [
            f"""
SOURCE:
{doc.metadata.get('source')}

{doc.page_content}
"""
            for doc in docs
        ]
    )

    history_text = "\n".join(
        [
            f"""
User:
{h['user']}

Assistant:
{h['assistant']}
"""
            for h in history[-5:]
        ]
    )

#     prompt = f"""
# You are an AI Career Coach.

# You have access to:

# 1. Candidate Resume
# 2. Job Description

# You can help with:

# - Resume questions
# - Interview preparation
# - Skill gap analysis
# - Career coaching
# - Technical tutoring
# - Project evaluation

# Instructions:

# - If the user asks about skills, explain them and relate them to the candidate's projects.
# - Never invent information.
# - If information is unavailable, say so.

# Conversation History:
# {history_text}

# Context:
# {context}

# Question:
# {query}

# Answer:
# """
    prompt = f"""
    You are an AI Career Coach.

    You have access to:

    1. Candidate Resume
    2. Job Description

    You can help with:

    - Resume questions
    - Interview preparation
    - Skill gap analysis
    - Career coaching
    - Technical tutoring
    - Project evaluation

    Instructions:

    - If the user asks about skills, explain them and relate them to the candidate's projects when possible.
    - If the user asks interview questions, generate realistic interview questions.
    - If the user asks for weaknesses or missing skills, compare the resume against the job description.
    - If the user asks which project best fits a role, justify your answer.
    - If information is unavailable, say so.
    - If user asks general questions or for advice, provide helpful guidance based on the context.
    
    Never invent information about the candidate. If the answer depends on the resume or job description and it is not present in the context, politely say you couldn't find it.

    Conversation History:
    {history_text}

    Context:
    {context}

    Question:
    {query}

    Answer:
"""

    for chunk in llm.stream(prompt):
        if chunk.content:
            yield chunk.content


# def ask_llm(
#         query,
#         session_id,
#         history
# ):


#     retriever = get_retriever(
#         session_id
#     )


#     if retriever is None:

#         return (
#             "Please upload your resume "
#             "and job description first."
#         )



#     docs = retriever.invoke(
#         query
#     )



#     context = "\n\n".join(

#         [
#             f"""
# SOURCE:
# {doc.metadata.get('source')}

# {doc.page_content}
# """
#             for doc in docs
#         ]

#     )



#     history_text = "\n".join(

#         [
#             f"""
# User:
# {h['user']}

# Assistant:
# {h['assistant']}
# """
#             for h in history[-5:]
#         ]

#     )



#     prompt = f"""
#     You are an AI Career Coach.

#     You have access to:

#     1. Candidate Resume
#     2. Job Description

#     You can help with:

#     - Resume questions
#     - Interview preparation
#     - Skill gap analysis
#     - Career coaching
#     - Technical tutoring
#     - Project evaluation

#     Instructions:

#     - If the user asks about skills, explain them and relate them to the candidate's projects when possible.
#     - If the user asks interview questions, generate realistic interview questions.
#     - If the user asks for weaknesses or missing skills, compare the resume against the job description.
#     - If the user asks which project best fits a role, justify your answer.
#     - If information is unavailable, say so.
#     - If user asks general questions or for advice, provide helpful guidance based on the context.
    
#     Never invent information about the candidate. If the answer depends on the resume or job description and it is not present in the context, politely say you couldn't find it.

#     Conversation History:
#     {history_text}

#     Context:
#     {context}

#     Question:
#     {query}

#     Answer:
# """



#     response = llm.invoke(
#         prompt
#     )


#     return response.content