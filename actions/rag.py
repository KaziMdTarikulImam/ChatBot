import os
import faiss
import numpy as np
from openai import AzureOpenAI
from typing import Any, Text, Dict, List
from sentence_transformers import SentenceTransformer
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from dotenv import load_dotenv

load_dotenv()


# ================================
# Global RAG Objects
# ================================
_rag_model = None
_rag_chunks = []
_rag_index = None


# ================================
# RAG Settings
# ================================
RAG_MODEL_NAME = "all-MiniLM-L6-v2"
RAG_DOCS_DIR = os.path.join(os.path.dirname(__file__), "rag_docs")

RAG_CHUNK_SIZE = 700
RAG_CHUNK_OVERLAP = 120
RAG_TOP_K = 4
RAG_SCORE_THRESHOLD = 0.35


# ================================
# Text Chunking
# ================================
def chunk_text(text: str, chunk_size: int = RAG_CHUNK_SIZE, overlap: int = RAG_CHUNK_OVERLAP) -> List[str]:
    """
    Split long text into overlapping chunks.
    This is better than only splitting by double newline.
    """

    text = " ".join(text.split())

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if len(chunk) > 80:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


# ================================
# Load Text Documents
# ================================
def load_text_documents() -> List[str]:
    """
    Load all .txt files from actions/rag_docs.
    Example:
    actions/rag_docs/devops.txt
    actions/rag_docs/aws.txt
    actions/rag_docs/profile.txt
    """

    chunks = []

    if not os.path.exists(RAG_DOCS_DIR):
        print(f"[RAG] Documents folder not found: {RAG_DOCS_DIR}")
        return chunks

    for filename in os.listdir(RAG_DOCS_DIR):
        if not filename.lower().endswith(".txt"):
            continue

        file_path = os.path.join(RAG_DOCS_DIR, filename)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                raw_text = file.read()

            file_chunks = chunk_text(raw_text)

            for chunk in file_chunks:
                chunks.append(f"Source: {filename}\n{chunk}")

            print(f"[RAG] Loaded {len(file_chunks)} chunks from {filename}")

        except Exception as e:
            print(f"[RAG] Failed to load {filename}: {e}")

    print(f"[RAG] Total chunks loaded: {len(chunks)}")
    return chunks


# ================================
# Load RAG Index
# ================================
def load_rag() -> None:
    """
    Lazy-load the embedding model and FAISS index.
    This runs only once when the first RAG question is asked.
    """

    global _rag_model, _rag_chunks, _rag_index

    if _rag_index is not None:
        return

    print("[RAG] Loading embedding model...")
    _rag_model = SentenceTransformer(RAG_MODEL_NAME)

    _rag_chunks = load_text_documents()

    if not _rag_chunks:
        print("[RAG] No chunks found. RAG will return empty context.")
        return

    print("[RAG] Creating embeddings...")
    embeddings = _rag_model.encode(
        _rag_chunks,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    embeddings = embeddings.astype("float32")

    dim = embeddings.shape[1]

    # IndexFlatIP + normalized embeddings = cosine similarity
    _rag_index = faiss.IndexFlatIP(dim)
    _rag_index.add(embeddings)

    print(f"[RAG] FAISS index ready with {len(_rag_chunks)} chunks.")


# ================================
# Retrieve Context
# ================================
def retrieve_context(query: str, top_k: int = RAG_TOP_K) -> str:
    """
    Retrieve the most relevant chunks for the user query.
    Returns context text to send into Azure OpenAI.
    """

    load_rag()

    if _rag_model is None or _rag_index is None or not _rag_chunks:
        return ""

    query_vector = _rag_model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    scores, indices = _rag_index.search(query_vector, top_k)

    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        if score >= RAG_SCORE_THRESHOLD:
            results.append(_rag_chunks[idx])

    return "\n\n".join(results)


# ================================
# Conversation History
# ================================
def get_conversation_history(tracker: Tracker, limit: int = 8) -> List[Dict[str, str]]:
    """
    Convert recent Rasa tracker events into OpenAI chat format.
    """

    history = []

    for event in tracker.events[-limit:]:
        if event.get("event") == "user" and event.get("text"):
            history.append({
                "role": "user",
                "content": event.get("text")
            })

        elif event.get("event") == "bot" and event.get("text"):
            history.append({
                "role": "assistant",
                "content": event.get("text")
            })

    return history


# ================================
# RAG System Prompt
# ================================
RAG_SYSTEM_PROMPT = """
I am Mohsin Rubel, a Senior DevOps Architect and Cloud Specialist.

My role is to answer questions using the retrieved knowledge base context first. The knowledge base may include my basic profile, education, certifications, professional summary, core expertise, cloud platform experience, employment history, project experience, tools, responsibilities, achievements, and technical background.

When the user asks about Mohsin Rubel, my profile, experience, job history, skills, certifications, education, cloud experience, DevOps tools, or career background, I must carefully extract the answer from the provided context and respond in first person using "I", "me", and "my".

I help with DevOps, cloud architecture, infrastructure automation, CI/CD, deployment, monitoring, logging, observability, containerization, Kubernetes, Terraform, networking, security, Linux servers, Windows servers, disaster recovery, and production support.

Context usage rules:
- Always prioritize the provided knowledge base context.
- If the answer exists in the context, use that information accurately.
- If multiple relevant details exist, combine them into a clear and concise answer.
- Do not ignore profile, education, certification, employment history, or experience details when they are relevant.
- If the context does not contain the exact answer, use general senior-level DevOps and cloud architecture knowledge only for technical questions.
- Never invent certifications, employers, client names, salaries, prices, dates, years of experience, locations, or project details.
- If the context is missing information about my personal background, say that the exact detail is not available in my knowledge base.

Identity rules:
- If someone asks who I am, introduce myself as Mohsin Rubel, a Senior DevOps Architect and Cloud Specialist.
- If someone asks about Mohsin Rubel, answer in first person using "I", "me", and "my".
- Do not speak about Mohsin Rubel in third person unless the user specifically asks for a third-person bio.
- Do not say "this person" or "the candidate" when answering about me.

Response rules:
- Reply in 2 to 4 short sentences maximum.
- Do not use bullet points unless the user asks for a list.
- Do not use markdown, tables, or code blocks unless requested.
- Keep responses concise, confident, professional, practical, and human-like.
- For technical questions, explain the real-world production best practice when helpful.
- If the user asks something outside DevOps, cloud engineering, infrastructure, automation, CI/CD, monitoring, security, or my professional background, politely say: "I can help with DevOps, cloud architecture, CI/CD, infrastructure, automation, deployment, monitoring, security, and my professional background."
- If you are unsure, say: "I’m not fully sure about that because the exact detail is not available in my knowledge base, but I can help with related DevOps and cloud guidance."
"""


# ================================
# Build Final LLM Messages
# ================================
def build_rag_messages(tracker: Tracker, user_message: str) -> List[Dict[str, str]]:
    """
    Builds final message list for Azure OpenAI.
    Includes recent chat history + retrieved context + latest question.
    """

    context = retrieve_context(user_message)

    history = get_conversation_history(tracker, limit=8)

    if context:
        final_user_prompt = f"""
        Relevant knowledge base context:
        {context}

        User question:
        {user_message}

        Answer using the context if relevant.
        """
    else:
        final_user_prompt = f"""
        No relevant knowledge base context was found.

        User question:
        {user_message}

        Answer based on general restaurant knowledge, but do not invent details.
        """

    messages = history + [
        {
            "role": "user",
            "content": final_user_prompt
        }
    ]

    return messages



# ================================
# Azure OpenAI Shared Function
# ================================
def get_llm_response(messages: list, system_prompt: str, max_tokens: int = 150) -> str:
    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )

    response = client.chat.completions.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        messages=[
            {
                "role": "system",
                "content": system_prompt
            }
        ] + messages,
        max_tokens=max_tokens,
        temperature=0.4,
    )

    return response.choices[0].message.content.strip()
