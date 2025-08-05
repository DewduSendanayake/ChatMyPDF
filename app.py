# app.py
import streamlit as st
from main import load_pdf, split_text, get_embedding_model, create_faiss_index, retrieve, generate_answer

# --- Sidebar: load PDF & build index ---
st.sidebar.title("📄 PDF Chatbot Setup")
pdf_file = st.sidebar.file_uploader("Upload a PDF", type="pdf")
if pdf_file:
    # Save uploaded file temporarily
    with open("uploaded.pdf", "wb") as f:
        f.write(pdf_file.getbuffer())

    text   = load_pdf("uploaded.pdf")
    chunks = split_text(text)
    embedder = get_embedding_model()
    index    = create_faiss_index(chunks, embedder)
    st.sidebar.success("✅ PDF indexed!")

    # --- Chat interface ---
    st.title("💬 PDF Chatbot")
    if "history" not in st.session_state:
        st.session_state.history = []

    question = st.text_input("Ask a question:")
    if st.button("Send") and question:
        st.session_state.history.append(("You", question))

        with st.spinner("⏳ Generating answer…"):
            context = retrieve(question, chunks, embedder, index)
            answer  = generate_answer(context, question)

        st.session_state.history.append(("Bot", answer))

    # Display chat history
    for speaker, text in st.session_state.history:
        if speaker == "You":
            st.markdown(f"**You:** {text}")
        else:
            st.markdown(f"**Bot:** {text}")

else:
    st.sidebar.info("Please upload a PDF to get started.")
