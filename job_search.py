from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool
from langchain_groq import ChatGroq
from pypdf import PdfReader
from docx import Document
import streamlit as st
import os
import tempfile
from dotenv import load_dotenv
from crewai import LLM


import crewai.llms.cache as _crewai_cache




# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="AI Multi-Agent Job Finder",
    page_icon="💼",
    layout="wide"
)

# Load environment variables
load_dotenv()


# --------------------------------------------------
# 2. API KEY VALIDATION
# --------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GROQ_API_KEY or not SERPER_API_KEY:
    st.error(
        "Missing API keys! Please configure "
        "GROQ_API_KEY and SERPER_API_KEY in your .env file."
    )
    st.stop()


# --------------------------------------------------
# 3. SIDEBAR CONFIGURATION
# --------------------------------------------------

with st.sidebar:

    st.header("⚙️ Configuration")

    st.success("Groq API Key Loaded")
    st.success("Serper API Key Loaded")

    selected_model = st.selectbox(
        "Select Groq Model",
        [
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "qwen/qwen3.8-27b"
        ],
        index=0
    )

    st.markdown("---")

    st.markdown(
        """
        ### Instructions

        1. Upload your resume.
        2. Select your preferred work mode.
        3. Enter your preferred location.
        4. Click Find Matching Jobs.

        The AI agents will analyze your CV
        and search for relevant job openings.
        """
    )


# --------------------------------------------------
# 4. RESUME TEXT EXTRACTION FUNCTION
# --------------------------------------------------

def extract_cv_text(uploaded_file):

    file_extension = uploaded_file.name.split(".")[-1].lower()

    if file_extension not in ["pdf", "docx"]:
        raise ValueError("Only PDF and DOCX files are supported.")

    text = ""

    tmp_path = None

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f".{file_extension}"
        ) as tmp:

            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        # Extract PDF content
        if file_extension == "pdf":

            reader = PdfReader(tmp_path)

            for page in reader.pages:

                extracted_text = page.extract_text()

                if extracted_text:
                    text += extracted_text + "\n"

        # Extract DOCX content
        elif file_extension == "docx":

            doc = Document(tmp_path)

            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"

            # Extract text from tables as well
            for table in doc.tables:

                for row in table.rows:

                    for cell in row.cells:
                        text += cell.text + " "

                    text += "\n"

    finally:

        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    return text.strip()


# --------------------------------------------------
# 5. MAIN APPLICATION UI
# --------------------------------------------------

st.title("💼 AI Multi-Agent Job Finder")

st.markdown(
    """
    Upload your resume and let our AI agents identify
    your skills, experience and suitable job opportunities.

    **Powered by CrewAI + Groq + Serper**
    """
)

col1, col2 = st.columns(2)

with col1:

    uploaded_cv = st.file_uploader(
        "Upload Your Resume",
        type=["pdf", "docx"],
        help="Upload a text-based PDF or DOCX resume."
    )

with col2:

    work_mode = st.selectbox(
        "Preferred Workplace Mode",
        [
            "Remote / WFH",
            "Hybrid",
            "Work from Office (WFO)",
            "Any / Flexible"
        ]
    )

preferred_location = st.text_input(
    "Preferred Job Location",
    placeholder="Example: Kolkata, Bangalore, India or Anywhere"
)

st.info(
    "Your resume content will be sent to the configured "
    "AI provider for analysis. Do not upload sensitive "
    "information you do not wish to share."
)


# --------------------------------------------------
# 6. JOB SEARCH EXECUTION
# --------------------------------------------------

if st.button(
    "🚀 Find Matching Jobs",
    type="primary",
    use_container_width=True
):

    if uploaded_cv is None:

        st.warning("Please upload your resume first.")

    else:

        try:

            with st.status(
                "🤖 AI Agents are working...",
                expanded=True
            ) as status:

                # ----------------------------------
                # STEP 1: EXTRACT RESUME CONTENT
                # ----------------------------------

                st.write("📄 Extracting resume information...")

                cv_content = extract_cv_text(uploaded_cv)

                if not cv_content.strip():

                    raise ValueError(
                        "No readable text found in your resume. "
                        "Please upload a text-based PDF or DOCX."
                    )

                st.success("Resume extracted successfully!")

                # ----------------------------------
                # STEP 2: INITIALIZE GROQ LLM
                # ----------------------------------

                st.write("🧠 Initializing Groq LLM...")

                from langchain_groq import ChatGroq


                llm = LLM(
                model="gemini/gemini-3.5-flash-lite",
               api_key=os.environ.get("GOOGLE_API_KEY"),
              temperature=0.2)

             

                # ----------------------------------
                # STEP 3: INITIALIZE SERPER TOOL
                # ----------------------------------

                st.write("🔍 Initializing Serper Search Tool...")

                search_tool = SerperDevTool()

                # ----------------------------------
                # STEP 4: DEFINE AGENT 1
                # CV ANALYZER
                # ----------------------------------

                cv_analyzer_agent = Agent(

                    role="Senior Technical Recruiter and CV Analyst",

                    goal=(
                        "Analyze candidate resumes and identify "
                        "skills, experience, seniority and suitable "
                        "job titles."
                    ),

                    backstory=(
                        "You are an experienced technical recruiter "
                        "with deep knowledge of the IT job market. "
                        "You understand technical skills, career "
                        "progression and candidate-job matching."
                    ),

                    llm=llm,

                    verbose=True,

                    allow_delegation=False,

                    max_iter=3
                )

                # ----------------------------------
                # STEP 5: DEFINE AGENT 2
                # JOB SEARCH AGENT
                # ----------------------------------

                job_search_agent = Agent(

                    role="Global Job Market Researcher",

                    goal=(
                        "Search the internet for relevant and "
                        "currently advertised job openings that "
                        "match the candidate's resume."
                    ),

                    backstory=(
                        "You are an expert job market researcher. "
                        "You use search engines to discover recent job "
                        "vacancies, company career pages and "
                        "recruitment portals. The jobs must not be expired."
                    ),

                    tools=[search_tool],

                    llm=llm,

                    verbose=True,

                    allow_delegation=False,

                    max_iter=5
                )

                # ----------------------------------
                # STEP 6: DEFINE TASK 1
                # RESUME ANALYSIS
                # ----------------------------------

                profile_task = Task(

                    description=f"""
                    Analyze the following candidate resume.

                    RESUME CONTENT:

                    {cv_content}

                    Perform the following analysis:

                    1. Identify the candidate's professional profile.
                    2. Extract technical and soft skills.
                    3. Identify programming languages and frameworks.
                    4. Estimate total years of experience if stated.
                    5. Identify seniority level.
                    6. Identify suitable job titles.
                    7. Identify relevant industries.
                    8. Identify important certifications.

                    Do not invent qualifications or experience.

                    If information is unavailable, mention that.

                    Provide a structured candidate profile.
                    """,

                    expected_output="""
                    A structured candidate profile containing:

                    - Professional Summary
                    - Technical Skills
                    - Soft Skills
                    - Years of Experience
                    - Seniority Level
                    - Suitable Job Titles
                    - Certifications
                    """,

                    agent=cv_analyzer_agent
                )

                # ----------------------------------
                # STEP 7: DEFINE TASK 2
                # JOB SEARCH
                # ----------------------------------

                search_task = Task(

                    description=f"""
                    Using the candidate profile generated
                    by the previous task, search the internet
                    for suitable job opportunities.

                    CANDIDATE LOCATION PREFERENCE:
                    {preferred_location if preferred_location.strip() else "Anywhere"}

                    WORK MODE PREFERENCE:
                    {work_mode}

                    REQUIREMENTS:

                    1. Search for relevant job openings using
                       the available Serper search tool.

                    2. Search company career pages, LinkedIn
                       job listings and other reputable
                       recruitment websites.

                    3. Find upto 5 top  job openings.

                    4. Match job requirements with the candidate's
                       technical skills and experience.

                    5. Exclude duplicate job listings.

                    6. Prioritize recently advertised vacancies.

                    7. Do not invent companies, job titles,
                       job descriptions or URLs.

                    8. Use direct job application URLs when
                       they are available in search results.

                    9. If only a general search or company
                       careers URL is available, clearly
                       identify it as such.

                    10. Do not claim that a vacancy is active
                        unless the search evidence supports it.

                    WORK MODE FILTERING:

                    - Remote / WFH:
                      Prefer jobs explicitly advertised as remote.

                    - Hybrid:
                      Prefer jobs explicitly advertised as hybrid.

                    - Work from Office:
                      Prefer jobs explicitly advertised as onsite.

                    - Any / Flexible:
                      Include all workplace modes.

                    Do not include jobs that contradict
                    the requested work mode.

                    If the work mode cannot be confirmed,
                    mark it as Not confirmed.

                    OUTPUT FORMAT:

                    For each job provide:

                    1. Job Title
                    2. Company Name
                    3. Location
                    4. Workplace Mode
                    5. Required Skills
                    6. Experience Required
                    7. Application URL
                    8. Why this job matches the candidate

                    Return fewer than five jobs if fewer
                    relevant and sufficiently supported
                    opportunities are found.

                    Do not fabricate missing information.
                    """,

                    expected_output="""
                    A structured Markdown report containing
                    up to five relevant job openings.

                    Each job should include the title,
                    company, location, work mode, required
                    experience, application URL and
                    candidate-job matching explanation.
                    """,

                    agent=job_search_agent,

                    context=[profile_task]
                )

                # ----------------------------------
                # STEP 8: ASSEMBLE CREW
                # ----------------------------------

                st.write("🤖 Creating the CrewAI workflow...")

                job_crew = Crew(

                    agents=[
                        cv_analyzer_agent,
                        job_search_agent
                    ],

                    tasks=[
                        profile_task,
                        search_task
                    ],

                    process=Process.sequential,

                    verbose=True
                )

                # ----------------------------------
                # STEP 9: EXECUTE CREW
                # ----------------------------------

                st.write(
                    "🔎 Analyzing CV and searching job portals..."
                )

                result = job_crew.kickoff()

                status.update(
                    label="✅ Job search completed!",
                    state="complete",
                    expanded=False
                )

            # ----------------------------------
            # STEP 10: DISPLAY RESULTS
            # ----------------------------------

            st.markdown("---")

            st.subheader("🎯 Your Matching Job Opportunities")

            st.markdown(str(result))

            st.success(
                "Your AI-powered job search is complete!"
            )

            # Option to download results
            st.download_button(
                label="📥 Download Job Search Report",
                data=str(result),
                file_name="job_search_report.md",
                mime="text/markdown"
            )

        except Exception as e:

            st.error(
                f"An error occurred: {str(e)}"
            )

            st.info(
                "Please check your API keys, Groq model "
                "availability, package versions and internet "
                "connection before trying again."
            )