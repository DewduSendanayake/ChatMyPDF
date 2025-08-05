# main.py

import os
import sys
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from llama_cpp import Llama

# 1) PDF loading
def load_pdf(file_path: str) -> str:
    if not os.path.isfile(file_path):
        print(f"❌ ERROR: PDF not found at '{file_path}'")
        sys.exit(1)
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"
    return text.strip()

# 2) Chunk splitting
def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    if not text:
        print("❌ ERROR: No text extracted from PDF.")
        sys.exit(1)
    splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_text(text)
    if not chunks:
        print("❌ ERROR: Text splitting produced zero chunks.")
        sys.exit(1)
    print(f"🔖 Split into {len(chunks)} chunks (chunk_size={chunk_size}, overlap={chunk_overlap})")
    return chunks

# 3) Embedding model
def get_embedding_model() -> SentenceTransformer:
    print("🧠 Loading embedding model 'all-MiniLM-L6-v2'...")
    return SentenceTransformer("all-MiniLM-L6-v2")

# 4) FAISS index creation
def create_faiss_index(chunks: list[str], embedder: SentenceTransformer):
    print("📦 Computing embeddings...")
    embeddings = embedder.encode(
        chunks,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    if embeddings.ndim != 2:
        print(f"❌ ERROR: Embeddings have unexpected shape {embeddings.shape}")
        sys.exit(1)
    dim = embeddings.shape[1]
    print(f"⚙️  Building FAISS index (dimension={dim})...")
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings.astype("float32"))
    print(f"✅ Indexed {embeddings.shape[0]} vectors.")
    return index

# 5) Retrieval
def retrieve(
    query: str,
    chunks: list[str],
    embedder: SentenceTransformer,
    index: faiss.Index,
    top_k: int = 3
) -> str:
    q_vec = embedder.encode(
        [query],
        convert_to_numpy=True
    ).astype("float32")
    distances, ids = index.search(q_vec, top_k)
    retrieved = [chunks[i] for i in ids[0]]
    print(f"🔍 Retrieved top {top_k} chunks (distances: {distances[0]})")
    return "\n\n".join(retrieved)

# 6) LLM answer generation
MODEL_PATH = "./models/Mistral-7B-Instruct-v0.1.Q4_K_M.gguf"
if not os.path.isfile(MODEL_PATH):
    print(f"❌ ERROR: Model not found at '{MODEL_PATH}'")
    sys.exit(1)

print(f"🤖 Loading LLM from {MODEL_PATH} (this can take 1–2 minutes)...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_threads=4
)

def generate_answer(context: str, question: str) -> str:
    prompt = f"""Use the following context to answer the question:

{context}

Question: {question}
Answer:"""
    out = llm(
        prompt,
        max_tokens=256,
        stop=["\n", "Question:"],
        echo=False
    )
    return out["choices"][0]["text"].strip()

# 7) Orchestrator
if __name__ == "__main__":
    PDF_PATH = "CV.pdf"  # <-- change to your PDF filename if different

    # Load & split PDF
    text    = load_pdf(PDF_PATH)
    chunks  = split_text(text)

    # Build FAISS index
    embedder = get_embedding_model()
    index    = create_faiss_index(chunks, embedder)

    # Interactive loop
    print("\n📖 PDF loaded and indexed. Type ‘exit’ to quit.\n")
    while True:
        question = input("❓ Ask: ").strip()
        if question.lower() in ("exit", "quit"):
            print("👋 Goodbye!")
            break
        context = retrieve(question, chunks, embedder, index)
        answer  = generate_answer(context, question)
        print("\n🤖 Answer:", answer, "\n")
