import streamlit as st
import os
import json
import pandas as pd
from google import genai

# Apni API Key yahan daalein
 "API_KEY = st.secrets["API_KEY"]"
MODEL_NAME = "gemini-3.6-flash"

COLUMNS = ["Q.No","Question","statement 1","statement 2","statement 3","statement 4",
"Table Left Column (List-I / Provisions) - Use \n for new row",
"Table Right Column (List-II / Articles) - Use \n for new row",
"Option A","Option B","Option C","Option D","Correct Answer","Explanation (Bullet Points)","Subject","Topic","Sub Topic"]

def clean(v):
    if v is None: return ""
    s = str(v).strip()
    if s.lower() in ["none","null","n/a","na","nil","-","no","not applicable"]: return ""
    return s

def process_pdf_to_excel(pdf_path, excel_path):
    client = genai.Client(api_key=API_KEY)
    uploaded_file = client.files.upload(file=pdf_path)
    while uploaded_file.state.name == "PROCESSING":
        import time
        time.sleep(1)
        uploaded_file = client.files.get(name=uploaded_file.name)

    prompt = """
    You are expert UPSC data operator. VERY STRICT RULES:
    1. QUESTION END RULE: Question ends at ?, : or ;. After that statements or pairs start. Question column must NOT contain statements/pairs.
    2. STATEMENT TYPE: "निम्नलिखित कथनों पर विचार कीजिए:" or "Consider following statements:" with "1. ... 2. ... 3. ..."
        -> Question = till ? : ;
        -> statement 1 = "1. ...", statement 2 = "2. ...", statement 3 = "3. ...", statement 4 = "4. ..." with number prefix "1. "
        -> Table Left, Table Right = "" blank
    3. YUGM / PAIR TYPE: "निम्नलिखित युग्मों में से कौन-सा सही सुमेलित है?" OR "निम्नलिखित युग्मों में से कितने युग्म सही सुमेलित हैं?"
        This type MUST go to TABLE, NOT statements.
        -> Question = that line only
        -> statement 1,2,3,4 = "" ALL BLANK
        -> Table Left Column = left side of all pairs separated by \\n
        -> Table Right Column = right side of all pairs separated by \\n
    4. LIST-I LIST-II TYPE: "Match List-I with List-II"
        -> Table Left = List-I items \\n separated
        -> Table Right = List-II items \\n separated
        -> statements blank
    5. NORMAL MCQ: Table blank, statements blank
    6. NEVER write "None", "none", "null". Use "" for blank.

    Return ONLY JSON array with keys:
    ["Q.No","Question","statement 1","statement 2","statement 3","statement 4",
    "Table Left Column (List-I / Provisions) - Use \\n for new row",
    "Table Right Column (List-II / Articles) - Use \\n for new row",
    "Option A","Option B","Option C","Option D","Correct Answer","Explanation (Bullet Points)","Subject","Topic","Sub Topic"]
    """

    response = client.models.generate_content(model=MODEL_NAME, contents=[uploaded_file, prompt])
    text = response.text.replace("```json","").replace("```","").strip()
    
    data = json.loads(text)
    fixed_data = []
    for row in data:
        for k in list(row.keys()):
            row[k] = clean(row[k])
        for i in range(1,5):
            key = f"statement {i}"
            v = row.get(key,"")
            if v:
                v = clean(v)
                if v and not v.startswith(f"{i}."):
                    v_tmp = v.lstrip("0123456789. ").strip()
                    if v_tmp:
                        v = f"{i}. {v_tmp}"
                row[key] = v
            else:
                row[key] = ""
        left_col = row.get("Table Left Column (List-I / Provisions) - Use \\n for new row","")
        q_text = row.get("Question","")
        if left_col and ("युग्म" in q_text or "युग्मों" in q_text):
            row["statement 1"] = row["statement 2"] = row["statement 3"] = row["statement 4"] = ""
        if "List-I" in q_text or "List-II" in q_text:
            row["statement 1"] = row["statement 2"] = row["statement 3"] = row["statement 4"] = ""
        fixed_data.append(row)

    df = pd.DataFrame(fixed_data)
    df = df.replace(["None","none","NULL","null","N/A"], "", regex=False).fillna("")
    df = df.reindex(columns=COLUMNS)
    df.to_excel(excel_path, index=False)

# --- STREAMLIT UI ---
st.set_page_config(page_title="UPSC PDF to Excel AI", page_icon="📄")
st.title("📄 UPSC PDF to Excel AI Converter")

uploaded_file = st.file_uploader("Apni PDF yahan upload karein", type=["pdf"])

if uploaded_file is not None:
    temp_pdf = "temp.pdf"
    output_excel = "output_format.xlsx"
    
    with open(temp_pdf, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    st.info("PDF upload ho gayi hai.")
    
    if st.button("Convert to Excel"):
        with st.spinner("AI processing chal rahi hai... Kripya intezaar karein."):
            try:
                process_pdf_to_excel(temp_pdf, output_excel)
                st.success("Excel file successfully ban gayi hai!")
                
                with open(output_excel, "rb") as file:
                    st.download_button(
                        label="📥 Download Excel File",
                        data=file,
                        file_name="UPSC_Output.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"Error aa gaya: {e}")