import os
import shutil
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    UploadFile,
    File
)

import uuid

from pydantic import BaseModel

from collections import defaultdict

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from rag import stream_llm
from rag import (
    add_document,
    reset_session,
    restore_sessions
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Starting InterviewPrepAI...")

    restore_sessions()

    yield

    print("Shutting down InterviewPrepAI...")

app = FastAPI(lifespan=lifespan)

# @app.on_event("startup")
# def startup():

#     restore_sessions()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



chat_history = defaultdict(list)



UPLOAD_DIR="uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)



class Query(BaseModel):

    message:str
    session_id:str





# @app.post("/chat")
# def chat(q:Query):


#     answer = ask_llm(
#         q.message,
#         q.session_id,
#         chat_history[q.session_id]
#     )


#     chat_history[q.session_id].append(

#         {
#             "user":q.message,
#             "assistant":answer
#         }

#     )


#     return {
#         "answer":answer
#     }


@app.post("/chat")
async def chat(q: Query):

    async def generate():

        full_response = ""

        for chunk in stream_llm(
            q.message,
            q.session_id,
            chat_history[q.session_id]
        ):

            full_response += chunk
            yield chunk

        chat_history[q.session_id].append(
            {
                "user": q.message,
                "assistant": full_response
            }
        )

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )




@app.post("/upload/resume")
async def upload_resume(
    session_id:str,
    file:UploadFile=File(...)
):


    path=f"{UPLOAD_DIR}/{session_id}_resume.pdf"


    with open(path,"wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )



    add_document(
        session_id,
        path,
        "resume",
        file.filename
    )


    chat_history[session_id]=[]


    return {
        "message":
        "Resume uploaded successfully"
    }







@app.post("/upload/job")
async def upload_job(

    session_id:str,
    file:UploadFile=File(...)

):


    path=f"{UPLOAD_DIR}/{session_id}_job.txt"



    with open(path,"wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )



    add_document(
        session_id,
        path,
        "job"
    )


    chat_history[session_id]=[]



    return {
        "message":
        "Job description uploaded successfully"
    }







@app.post("/reset")
def reset(
    session_id:str
):

    reset_session(
        session_id
    )


    chat_history.pop(
        session_id,
        None
    )


    return {
        "message":
        "Session reset"
    }
    
    

@app.get("/session")
def create_session():

    session_id = str(uuid.uuid4())

    return {
        "session_id": session_id
    }
    
@app.get("/session/status/{session_id}")
def session_status(session_id: str):

    from rag import user_documents

    documents = user_documents.get(
        session_id,
        {}
    )


    resume = documents.get("resume")
    job = documents.get("job")

    job_text = ""

    if job:
        with open(job["path"], "r", encoding="utf-8") as f:
            job_text = f.read()

    return {
        "resume": resume["filename"] if resume else None,
        "job_description": job_text
    }
    # return {
    #     "resume": (
    #         os.path.basename(documents["resume"])
    #         if documents.get("resume")
    #         else None
    #     ),

    #     "job_uploaded": (
    #         True
    #         if documents.get("job")
    #         else False
    #     )
    # }