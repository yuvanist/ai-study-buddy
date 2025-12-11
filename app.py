from __future__ import annotations

import os
from typing import List, Literal, Optional, Union

import streamlit as st
from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, conlist


load_dotenv()


# ---------- Pydantic models for structured output ----------
class MultipleChoiceQuestion(BaseModel):
    question: str
    options: conlist(str, min_length=2)
    answer: str
    explanation: Optional[str] = None


class FillBlankQuestion(BaseModel):
    question: str
    answer: str
    explanation: Optional[str] = None


class QuestionSet(BaseModel):
    persona: str
    topic: str
    difficulty: str
    question_type: Literal["multiple_choice", "fill_blank"]
    questions: List[Union[MultipleChoiceQuestion, FillBlankQuestion]]


def build_agent(provider: str, model_name: str, api_key: str, persona: str) -> Agent:
    system_prompt = (
        f"You are {persona}, an adaptive study buddy. "
        "Generate concise, correct educational content. "
        "Respond using the provided structured schema; no markdown or prose."
    )

    if provider == "OpenAI":
        model = OpenAIChat(id=model_name, api_key=api_key)
    else:
        model = Groq(id=model_name, api_key=api_key)

    # Agno will use Structured Outputs when supported; otherwise it falls back
    # to JSON mode while still returning a Pydantic object per docs:
    # https://docs.agno.com/faq/structured-outputs
    return Agent(
        model=model,
        instructions=system_prompt,
        output_schema=QuestionSet,
        use_json_mode=False,
    )


def generate_question_set(
    agent: Agent,
    topic: str,
    question_type: Literal["multiple_choice", "fill_blank"],
    difficulty: str,
    num_questions: int,
    persona: str,
) -> QuestionSet:
    prompt = (
        "Create study questions following the provided schema. "
        f"- question_type: {question_type}\n"
        f"- topic: {topic}\n"
        f"- number_of_questions: {num_questions}\n"
        f"- difficulty: {difficulty}\n"
        "- Keep explanations brief; ensure answers are unambiguous.\n"
        "- For multiple_choice, provide 3-5 distinct options; 'answer' must exactly match one option.\n"
        "- For fill_blank, provide a clear blank statement and the precise answer.\n"
    )

    response = agent.run(prompt)
    if isinstance(response, QuestionSet):
        return response
    if isinstance(response, BaseModel):
        return QuestionSet.model_validate(response.model_dump())
    if isinstance(response, dict):
        return QuestionSet.model_validate(response)
    raise ValueError("Model did not return a structured QuestionSet.")


def format_for_download(qset: QuestionSet) -> str:
    lines = [
        f"Persona: {qset.persona}",
        f"Topic: {qset.topic}",
        f"Difficulty: {qset.difficulty}",
        f"Question type: {qset.question_type}",
        "",
    ]

    for idx, q in enumerate(qset.questions, start=1):
        lines.append(f"Q{idx}. {q.question}")
        if isinstance(q, MultipleChoiceQuestion):
            for opt in q.options:
                lines.append(f" - {opt}")
        lines.append(f"Answer: {q.answer}")
        if q.explanation:
            lines.append(f"Why: {q.explanation}")
        lines.append("")
    return "\n".join(lines)


# ---------- Streamlit UI ----------
st.set_page_config(
    page_title="AI Study Buddy (Agno + Streamlit)",
    page_icon="📚",
    layout="wide",
)

st.title("AI Study Buddy")
st.caption("Agno-powered, multi-model (Groq/OpenAI), persona-aware study question generator.")

with st.sidebar:
    st.header("Model & Persona")
    provider = st.radio("Provider", ["Groq", "OpenAI"], index=0)
    model_options = {
        "Groq": [
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-safeguard-20b",
            "moonshotai/kimi-k2-instruct-0905",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ],
        "OpenAI": [
            "gpt-5.1-mini",
            "gpt-5.1-nano",
        ],
    }
    model_name = st.selectbox("Model", model_options[provider])

    default_groq = os.getenv("GROQ_API_KEY", "")
    default_openai = os.getenv("OPENAI_API_KEY", "")
    api_key = st.text_input(
        f"{provider} API key",
        value=default_groq if provider == "Groq" else default_openai,
        type="password",
        help="Key is kept in this session only.",
    )

    persona = st.selectbox(
        "Persona",
        [
            "Friendly mentor",
            "Concise explainer",
            "Tough coach",
            "Enthusiastic tutor",
        ],
    )

st.subheader("Question Settings")
topic = st.text_input("Topic", placeholder="e.g., Photosynthesis, Calculus integrals")
question_type_label = st.radio("Question type", ["Multiple choice", "Fill in the blanks"], index=0)
question_type_value = "multiple_choice" if question_type_label == "Multiple choice" else "fill_blank"
difficulty = st.select_slider("Difficulty", options=["easy", "medium", "hard"], value="medium")
num_questions = st.slider("Number of questions", min_value=1, max_value=5, value=3)

if "last_qset" not in st.session_state:
    st.session_state["last_qset"] = None

if st.button("Generate questions", type="primary"):
    if not api_key:
        st.error(f"Please provide your {provider} API key.")
    elif not topic.strip():
        st.error("Please enter a topic.")
    else:
        with st.spinner("Calling the agent..."):
            try:
                agent = build_agent(provider, model_name, api_key, persona)
                qset = generate_question_set(agent, topic, question_type_value, difficulty, num_questions, persona)
                st.session_state["last_qset"] = qset
                st.success("Generated questions!")
            except (ValidationError, ValueError) as exc:
                st.error(f"Could not parse structured output: {exc}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Agent call failed: {exc}")


qset: Optional[QuestionSet] = st.session_state.get("last_qset")
if qset:
    st.divider()
    st.subheader("Questions & Answers")
    for idx, q in enumerate(qset.questions, start=1):
        st.markdown(f"**Q{idx}. {q.question}**")
        if isinstance(q, MultipleChoiceQuestion):
            for opt in q.options:
                bullet = "✅" if opt.strip().lower() == q.answer.strip().lower() else "•"
                st.write(f"{bullet} {opt}")
        st.write(f"**Answer:** {q.answer}")
        if q.explanation:
            st.caption(q.explanation)
        st.markdown("---")

    download_text = format_for_download(qset)
    st.download_button(
        label="Download as .txt",
        data=download_text,
        file_name=f"study-buddy-{qset.topic.replace(' ', '-')}.txt",
        mime="text/plain",
    )

