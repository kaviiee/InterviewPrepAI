"use client";
import ReactMarkdown from "react-markdown";
import { useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
};

export default function Home() {

  const [message, setMessage] = useState("");
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState("");

  const [resume, setResume] = useState<string | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [jobSaved, setJobSaved] = useState(false);
  const [uploadingResume, setUploadingResume] = useState(false);
  const [uploadingJob, setUploadingJob] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {

  chatEndRef.current?.scrollIntoView({
    behavior: "smooth"
  });

}, [chat]);

  // useEffect(() => {

  //   let stored = localStorage.getItem("session_id");

  //   if (!stored) {
  //     stored = crypto.randomUUID();
  //     localStorage.setItem("session_id", stored);
  //   }

  //   setSessionId(stored);

  // }, []);


//   useEffect(() => {

//   async function createSession() {

//     let stored = localStorage.getItem("session_id");

//     // Existing user/session
//     if (stored) {
//       setSessionId(stored);
//       return;
//     }


//     // New user/session
//     const res = await fetch(
//       "http://127.0.0.1:8000/session"
//     );

//     const data = await res.json();

//     localStorage.setItem(
//       "session_id",
//       data.session_id
//     );

//     setSessionId(
//       data.session_id
//     );
//   }


//   createSession();

// }, []);

useEffect(() => {

  async function initializeSession() {

    let stored = localStorage.getItem("session_id");


    // create new session
    if (!stored) {
      const res = await fetch(`${API_URL}/session`);
      const data = await res.json();
      if (!data.session_id) {
          throw new Error("Failed to create session");
      }
      stored = data.session_id as string;

      localStorage.setItem("session_id", stored);
      // const res = await fetch(
      //   `${API_URL}/session`
      //   // "http://127.0.0.1:8000/session"
      // );


      // const data = await res.json();
      
      // const newSessionId: string = data.session_id;


      // // stored = data.session_id;


      // localStorage.setItem(
      //   "session_id",
      //   newSessionId
      // );

    }
    if (!stored) return;

    setSessionId(stored);



    // restore uploaded documents

    const statusRes = await fetch(
      `${API_URL}/session/status/${stored}`
      // "http://localhost:8000/session/status/${stored}"
    );


    const status = await statusRes.json();



    if(status.resume){

      setResume(
        status.resume
      );

    }

    if (status.job_description) {
      setJobDescription(status.job_description);
      setJobSaved(true);
    }
    // if(status.job_uploaded){

    //   setJobSaved(true);

    // }

  }


  initializeSession();


}, []);


  // async function sendMessage() {

  //   if (!message.trim() || !sessionId) return;

  //   const userMessage = message;

  //   setChat(prev => [
  //     ...prev,
  //     {
  //       role: "user",
  //       text: userMessage
  //     }
  //   ]);

  //   setMessage("");


  //   const res = await fetch(
  //     "http://127.0.0.1:8000/chat",
  //     {
  //       method: "POST",
  //       headers:{
  //         "Content-Type":"application/json"
  //       },
  //       body:JSON.stringify({
  //         message:userMessage,
  //         session_id:sessionId
  //       })
  //     }
  //   );


  //   const data = await res.json();


  //   setChat(prev => [
  //     ...prev,
  //     {
  //       role:"assistant",
  //       text:data.answer
  //     }
  //   ]);
  // }

  async function sendMessage() {

  if (!message.trim()) return;

  const userMessage = message;

  setMessage("");

  // Add user message
  setChat(prev => [
    ...prev,
    {
      role: "user",
      text: userMessage
    }
  ]);

  // Empty assistant message
  setChat(prev => [
    ...prev,
    {
      role: "assistant",
      text: ""
    }
  ]);

  const res = await fetch(
    // "http://127.0.0.1:8000/chat",
    `${API_URL}/chat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: userMessage,
        session_id: sessionId
      })
    }
  );

  if (!res.body) return;

  const reader = res.body.getReader();

  const decoder = new TextDecoder();

  let fullText = "";

  while (true) {

    const { done, value } = await reader.read();

    if (done) break;

    fullText += decoder.decode(value);

    setChat(prev => {

      const updated = [...prev];

      updated[updated.length - 1] = {
        role: "assistant",
        text: fullText
      };

      return updated;

    });

  }

}

  // function uploadResume(e: React.ChangeEvent<HTMLInputElement>) {

  //   const file = e.target.files?.[0];

  //   if(file){
  //     setResume(file.name);
  //   }

  // }
  async function uploadJobDescription() {

  if (!jobDescription.trim() || !sessionId) return;


  setUploadingJob(true);


  const blob = new Blob(
    [
      jobDescription
    ],
    {
      type:"text/plain"
    }
  );


  const file = new File(
    [
      blob
    ],
    "job_description.txt"
  );


  const formData = new FormData();

  formData.append(
    "file",
    file
  );


  try {

    const res = await fetch(
      // `http://127.0.0.1:8000/upload/job?session_id=${sessionId}`,
      `${API_URL}/upload/job?session_id=${sessionId}`,
      {
        method:"POST",
        body:formData
      }
    );


    const data = await res.json();

    console.log(data);


    setJobSaved(true);


    setChat(prev=>[
      ...prev,
      {
        role:"assistant",
        text:
        "Job description updated. I rebuilt your knowledge base."
      }
    ]);


  }
  finally {

    setUploadingJob(false);

  }

}

  async function uploadResume(
    e: React.ChangeEvent<HTMLInputElement>
  ) {

    const file = e.target.files?.[0];

    if (!file || !sessionId) return;

    setUploadingResume(true);

    const formData = new FormData();

    formData.append(
      "file",
      file
    );

    try{
    const res = await fetch(
      // `http://127.0.0.1:8000/upload/resume?session_id=${sessionId}`,
      `${API_URL}/upload/resume?session_id=${sessionId}`,
      {
        method:"POST",
        body:formData
      }
    );


    const data = await res.json();


    console.log(data);


    setResume(file.name);


    setChat(prev => [
      ...prev,
      {
        role:"assistant",
        text:"Resume uploaded successfully. Your knowledge base has been updated."
      }
    ]);
    }
    finally{
      setUploadingResume(false);
    }

  }



  return (

    <div className="h-screen flex bg-gray-100">


      {/* LEFT SIDEBAR */}

      <aside className="w-80 bg-white border-r p-6 flex flex-col gap-6">


        <h1 className="text-2xl font-bold">
          InterviewPrepAI
        </h1>



        {/* Resume */}

        <div className="border rounded-xl p-4">

          <h2 className="font-semibold mb-3">
            📄 Resume
          </h2>


          {
            resume ?

            <div className="text-sm text-green-600 mb-3">
              ✓ {resume}
            </div>

            :

            <div className="text-sm text-gray-500 mb-3">
              No resume uploaded
            </div>

          }

{/* 
          <label
            className="
            cursor-pointer
            bg-blue-600
            text-white
            px-4
            py-2
            rounded-lg
            text-sm
            inline-block
            "
          >

            Upload Resume

            <input
              type="file"
              accept=".pdf"
              hidden
              onChange={uploadResume}
            />

          </label> */}

  <label
    className={`
      cursor-pointer
      bg-blue-600
      text-white
      px-4
      py-2
      rounded-lg
      text-sm
      inline-block
      ${!sessionId || uploadingResume 
        ? "opacity-50 cursor-not-allowed"
        : ""}
    `}
  >

    {
      uploadingResume
      ?
      "Uploading..."
      :
      resume
      ?
      "Replace Resume"
      :
      "Upload Resume"
    }


    <input
      type="file"
      accept=".pdf"
      hidden
      disabled={!sessionId || uploadingResume}
      onChange={uploadResume}
    />

  </label>



        </div>





        {/* JOB DESCRIPTION */}


        <div className="border rounded-xl p-4 flex-1">


          <h2 className="font-semibold mb-3">
            📋 Job Description
          </h2>



          <textarea

            value={jobDescription}

            onChange={
              e=>setJobDescription(e.target.value)
            }

            placeholder="
Paste job description here..."
            
            className="
            w-full
            h-40
            border
            rounded-lg
            p-3
            text-sm
            resize-none
            "

          />


{/* 
          <button

            className="
            mt-3
            bg-gray-800
            text-white
            px-4
            py-2
            rounded-lg
            text-sm
            "

          >

            Save Job Description

          </button> */}
          {/* <button

onClick={async()=>{


  const blob = new Blob(
    [
      jobDescription
    ],
    {
      type:"text/plain"
    }
  );


  const file = new File(
    [
      blob
    ],
    "job_description.txt"
  );



  const formData = new FormData();

  formData.append(
    "file",
    file
  );



  const res = await fetch(

    `http://127.0.0.1:8000/upload/job?session_id=${sessionId}`,

    {
      method:"POST",
      body:formData
    }

  );


  const data = await res.json();


  console.log(data);



  setJobSaved(true);



  setChat(prev=>[
    ...prev,
    {
      role:"assistant",
      text:
      "Job description saved. I can now analyze your resume against this role."
    }
  ]);



}}

className="
mt-3
bg-gray-800
text-white
px-4
py-2
rounded-lg
text-sm
"

>

{
jobSaved
?
"✓ Job Description Saved"
:
"Save Job Description"
}

</button> */}
<button

onClick={uploadJobDescription}

disabled={
  !sessionId ||
  !jobDescription.trim() ||
  uploadingJob
}

className={`
mt-3
bg-gray-800
text-white
px-4
py-2
rounded-lg
text-sm

${
  (!sessionId || !jobDescription.trim() || uploadingJob)
  ?
  "opacity-50 cursor-not-allowed"
  :
  ""
}

`}

>

{
uploadingJob
?
"Updating..."

:

jobSaved
?
"✓ Job Description Updated"

:
"Save Job Description"
}

</button>

        </div>





        <button

          // onClick={()=>{
          //   setChat([]);
          //   localStorage.removeItem("session_id");
          //   window.location.reload();
          // }}

          onClick={async()=>{


 await fetch(

//  `http://127.0.0.1:8000/reset?session_id=${sessionId}`,
 `${API_URL}/reset?session_id=${sessionId}`,

 {
 method:"POST"
 }

 );


 setChat([]);

 setResume(null);

 setJobDescription("");

 setJobSaved(false);


}}

          className="
          text-red-500
          border
          rounded-lg
          py-2
          "

        >

          Reset Session

        </button>


      </aside>






      {/* CHAT AREA */}


      <main className="flex-1 flex flex-col">


        <header className="
        bg-white
        border-b
        p-5
        font-semibold
        ">

          AI Career Coach

        </header>





        <div className="
        flex-1
        overflow-y-auto
        p-6
        space-y-4
        ">


          {
            chat.length===0 &&

            <div className="
            text-gray-400
            text-center
            mt-20
            ">

              Upload your resume and job description
              <br/>
              then start preparing!

            </div>

          }



          {
            chat.map((c,i)=>(

              <div
              key={i}
              className={`
              flex
              ${c.role==="user"
                ?"justify-end"
                :"justify-start"}
              `}
              >


                {/* <div

                className={`
                max-w-2xl
                p-4
                rounded-xl

                ${
                  c.role==="user"

                  ?
                  "bg-blue-600 text-white"

                  :
                  "bg-white border"

                }

                `}

                >

                  {c.text}

                </div> */}
                <div

className={`

max-w-2xl
p-4
rounded-xl
prose

${
  c.role==="user"

  ?

  "bg-blue-600 text-white"

  :

  "bg-white border"

}

`}

>


{
c.role === "assistant"

?

<ReactMarkdown>
  {c.text}
</ReactMarkdown>


:

c.text

}


</div>

              </div>


            ))
          }
          <div ref={chatEndRef}></div>


        </div>







        {/* INPUT */}


        <div className="
        bg-white
        border-t
        p-4
        flex
        gap-3
        ">


          <input

            value={message}

            onChange={
              e=>setMessage(e.target.value)
            }

            onKeyDown={
              e=>{
                if(e.key==="Enter")
                  sendMessage();
              }
            }


            placeholder="Ask about your resume, interview, skills..."

            className="
            flex-1
            border
            rounded-xl
            px-4
            "

          />



          <button

            onClick={sendMessage}

            className="
            bg-blue-600
            text-white
            px-6
            rounded-xl
            "

          >

            Send

          </button>



        </div>


      </main>


    </div>

  );
}