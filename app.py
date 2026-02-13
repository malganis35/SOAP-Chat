import streamlit as st
from groq import Groq
import os
import io
import docx

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Medical SOAP Note Generator", page_icon="⚕️", layout="wide")

# --- LOAD PROMPTS FROM FOLDER ---
def load_prompts(directory="prompts"):
    prompts = {}
    if not os.path.exists(directory):
        os.makedirs(directory)
        with open(os.path.join(directory, "Standard_SOAP.txt"), "w", encoding="utf-8") as f:
            f.write("You are an expert medical assistant. Convert the provided raw medical notes into a structured SOAP format (Subjective, Objective, Assessment, Plan). Be precise, objective, clear, and strictly use these four headings.")
    
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            style_name = filename.replace(".txt", "").replace("_", " ")
            with open(os.path.join(directory, filename), "r", encoding="utf-8") as f:
                prompts[style_name] = f.read()
    
    return prompts

PROMPT_STYLES = load_prompts()

# --- HELPER FUNCTION: CREATE DOCX ---
def create_docx(text):
    doc = docx.Document()
    doc.add_paragraph(text)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Configuration")
    st.markdown("""
    **Medical SOAP Generator**
    Transform raw clinical notes into structured SOAP notes using AI.
    """)
    st.divider()
    
    api_key_input = st.text_input("Enter your Groq API Token:", type="password")
    
    if not PROMPT_STYLES:
        st.warning("No prompts found in the 'prompts/' folder.")
        selected_style = None
    else:
        selected_style = st.selectbox("Choose Prompt Template:", list(PROMPT_STYLES.keys()))
    
    if st.button("Reset Application"):
        st.session_state.generated_soap = ""
        st.rerun()

# --- MAIN INTERFACE ---
st.title("⚕️ Medical SOAP Note Generator")
st.markdown("Convert raw consultation notes into the standardized **Subjective, Objective, Assessment, Plan** format.")
st.divider()

if "generated_soap" not in st.session_state:
    st.session_state.generated_soap = ""

# --- 1. INPUT SECTION ---
st.subheader("1. Input Raw Medical Notes")
input_method = st.radio("Choose input method:", ["Paste raw text", "Upload file (.txt, .docx)"], horizontal=True)

raw_notes = ""

if input_method == "Paste raw text":
    raw_notes = st.text_area("Paste the raw medical notes here:", height=200, placeholder="E.g., Patient came in complaining of a headache for 3 days...")
else:
    uploaded_file = st.file_uploader("Upload a file containing raw notes", type=["txt", "docx"])
    if uploaded_file is not None:
        # Extract text based on file type
        if uploaded_file.name.endswith('.txt'):
            raw_notes = uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith('.docx'):
            doc = docx.Document(uploaded_file)
            raw_notes = "\n".join([para.text for para in doc.paragraphs])
            
        st.success("File loaded successfully!")
        with st.expander("Preview raw notes"):
            st.write(raw_notes)

# --- 2. GENERATION SECTION ---
st.subheader("2. Generate Structured SOAP Note")

if st.button("Generate SOAP Note", type="primary"):
    if not api_key_input:
        st.error("Please enter your Groq API key in the sidebar to start.")
    elif not raw_notes.strip():
        st.warning("Please provide some raw medical notes to process.")
    elif not selected_style:
        st.error("Please ensure you have at least one prompt in the 'prompts/' folder.")
    else:
        try:
            client = Groq(api_key=api_key_input)
            
            system_prompt = PROMPT_STYLES[selected_style]
            user_message = f"Please structure the following raw clinical notes into a SOAP format:\n\n{raw_notes}"
            
            full_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            with st.spinner("Analyzing and structuring notes..."):
                message_placeholder = st.empty()
                full_response = ""
                
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=full_messages,
                    temperature=0.3,
                    max_tokens=2048,
                    stream=True,
                )

                for chunk in completion:
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                st.session_state.generated_soap = full_response

        except Exception as e:
            st.error(f"API Error: {e}")

# --- 3. EXPORT SECTION ---
if st.session_state.generated_soap:
    st.divider()
    st.subheader("3. Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="📄 Download as .TXT",
            data=st.session_state.generated_soap,
            file_name="Structured_SOAP_Note.txt",
            mime="text/plain",
            use_container_width=True
        )
        
    with col2:
        docx_file = create_docx(st.session_state.generated_soap)
        st.download_button(
            label="📝 Download as .DOCX",
            data=docx_file,
            file_name="Structured_SOAP_Note.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )