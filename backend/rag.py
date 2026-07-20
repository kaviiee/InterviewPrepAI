import os
import shutil
from pathlib import Path
import json

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader
)

# from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv


load_dotenv()

FAISS_STORAGE_PATH = Path("storage/faiss")

FAISS_STORAGE_PATH.mkdir(
    parents=True,
    exist_ok=True
)

SESSION_FILE = FAISS_STORAGE_PATH.parent / "sessions.json"

# embeddings = HuggingFaceEmbeddings(
#     model_name="sentence-transformers/all-MiniLM-L6-v2"
# )

# embeddings = HuggingFaceInferenceAPIEmbeddings(
#     api_key=os.getenv("HF_TOKEN"),
#     model_name="sentence-transformers/all-MiniLM-L6-v2"
# )


embeddings = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    provider="hf-inference"

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

def get_faiss_path(session_id):

    path = FAISS_STORAGE_PATH / session_id

    path.mkdir(
        parents=True,
        exist_ok=True
    )

    return str(path)


def save_vector_db(session_id, db):

    path = get_faiss_path(session_id)
    
    print("Saving FAISS index to:", path)

    db.save_local(
        path
    )
    print("FAISS save complete")


def save_sessions():

    with open(
        SESSION_FILE,
        "w"
    ) as f:

        json.dump(
            user_documents,
            f,
            indent=4
        )



def load_sessions():

    global user_documents

    if not SESSION_FILE.exists():
        return


    with open(
        SESSION_FILE,
        "r"
    ) as f:

        user_documents = json.load(f)


def load_vector_db(session_id):

    path = get_faiss_path(session_id)

    index_file = os.path.join(
        path,
        "index.faiss"
    )

    if not os.path.exists(index_file):
        return None


    db = FAISS.load_local(
        path,
        embeddings,
        allow_dangerous_deserialization=True
    )

    return db

def restore_sessions():
    
    load_sessions()

    if not FAISS_STORAGE_PATH.exists():
        return


    for session_id in os.listdir(
        FAISS_STORAGE_PATH
    ):

        db = load_vector_db(
            session_id
        )

        if db is not None:

            user_db[session_id] = db


            user_retriever[session_id] = (
                db.as_retriever(
                    search_type="mmr",
                    search_kwargs={
                        "k":10,
                        "fetch_k":30
                    }
                )
            )

            print(
                f"Restored FAISS index for {session_id}"
            )
            
            
def build_vector_db(session_id):

    docs = []


    # files = user_documents.get(
    #     session_id,
    #     []
    # )

    documents = user_documents.get(session_id, {})

    # files = [
    #     path 
    #     for path in documents.values()
    #     if path is not None
    # ]
    files = []

    resume = documents.get("resume")
    job = documents.get("job")

    if resume:
        files.append(resume["path"])

    if job:
        files.append(job["path"])
    
    
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


    save_vector_db(
        session_id,
        db
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

def add_document(session_id, file_path, document_type, original_filename=None):

    if session_id not in user_documents:
        user_documents[session_id] = {
            "resume": None,
            "job": None
        }


    # user_documents[session_id][document_type] = file_path
    if document_type == "resume":

        user_documents[session_id]["resume"] = {
            "path": file_path,
            "filename": original_filename
            # os.path.basename(file_path)
        }

    else:

        user_documents[session_id]["job"] = {
            "path": file_path
        }
        
    save_sessions()
    
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

    # user_documents.pop(
    #     session_id,
    #     None
    # )
    if session_id in user_documents:
        user_documents.pop(session_id)
    user_db.pop(
        session_id,
        None
    )

    user_retriever.pop(
        session_id,
        None
    )

    faiss_path = FAISS_STORAGE_PATH / session_id

    if faiss_path.exists():

        shutil.rmtree(
            faiss_path
        )
    save_sessions()




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