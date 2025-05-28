import streamlit as st
import pandas as pd
import sqlite3
import os

# --- Page setup ---
st.set_page_config(page_title="Company Uploader", layout="wide")
st.title("📤 Upload Company Excel Files")
st.markdown("Upload multiple Excel files. All data is saved and searchable across sessions.")

# --- Database setup ---
DB_PATH = "company_data.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Create table only once
cursor.execute("""
CREATE TABLE IF NOT EXISTS companies (
    CIN TEXT PRIMARY KEY,
    Name TEXT,
    State TEXT,
    Email TEXT
)
""")
conn.commit()

# --- Upload and process Excel file ---
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    expected_columns = ['CIN', 'Name', 'State', 'Email']

    # Fix headers
    if df.shape[1] >= 4:
        first_row = df.iloc[0].astype(str).str.upper().tolist()
        if first_row[:4] == [col.upper() for col in expected_columns]:
            df = df[1:]
    
    df.columns = expected_columns
    df = df[expected_columns]
    df = df.drop_duplicates(subset="CIN")
    
    # Clean and normalize text fields
    for col in expected_columns:
        df[col] = df[col].astype(str).str.strip()

    # Insert data into DB without duplicates
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR IGNORE INTO companies (CIN, Name, State, Email)
            VALUES (?, ?, ?, ?)
        """, (row['CIN'], row['Name'], row['State'], row['Email']))
    conn.commit()

    st.success(f"✅ {len(df)} companies uploaded and added to database.")
    st.dataframe(df)

# --- Search form ---
st.markdown("---")
st.subheader("🔍 Search Company by Name")

search_name = st.text_input("Enter full or partial company name").strip().lower()

if search_name:
    cursor.execute("""
        SELECT * FROM companies WHERE LOWER(Name) LIKE ?
    """, ('%' + search_name + '%',))
    results = cursor.fetchall()

    if results:
        st.success(f"Found {len(results)} result(s):")
        for cin, name, state, email in results:
            st.markdown(f"""
            🏢 **Company Name**: `{name}`  
            🆔 **CIN**: `{cin}`  
            📍 **State**: `{state}`  
            📧 **Email**: `{email}`  
            ---""")
    else:
        st.warning("No matching company found.")

# --- Optional: Show full DB contents for debugging ---
with st.expander("📋 View All Stored Companies (Debugging)"):
    df_all = pd.read_sql_query("SELECT * FROM companies", conn)
    st.dataframe(df_all)
