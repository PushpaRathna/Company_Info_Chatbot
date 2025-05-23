import streamlit as st
import pandas as pd
import sqlite3

st.title("📤 Upload Company Excel File")

# Connect to SQLite DB (creates file if not exists)
conn = sqlite3.connect("company_data.db", check_same_thread=False)
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS companies (
    CIN TEXT,
    Name TEXT,
    State TEXT,
    Email TEXT
)
""")
conn.commit()

# Initialize session_state dataframe if not present
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

# Upload Excel file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    
    # Insert new rows into DB
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO companies (CIN, Name, State, Email)
            VALUES (?, ?, ?, ?)
        """, (row['CIN'], row['Name'], row['State'], row['Email']))
    conn.commit()

    # Update in-memory dataframe as well (optional, for display)
    st.session_state.df = pd.concat([st.session_state.df, df], ignore_index=True)

    st.success("File uploaded and data stored in database!")
    st.dataframe(st.session_state.df)  # Show combined data uploaded so far

st.markdown("---")
st.subheader("🔍 Search Company Info")

search_name = st.text_input("Enter company name")

if search_name:
    cursor.execute("SELECT * FROM companies WHERE Name LIKE ?", ('%' + search_name + '%',))
    results = cursor.fetchall()

    if results:
        st.success(f"Found {len(results)} result(s):")
        for cin, name, state, email in results:
            st.markdown(f"""
            📄 **Company Name**: `{name}`  
            🏷️ **CIN**: `{cin}`  
            🗺️ **State**: `{state}`  
            📧 **Email**: `{email}`  
            ---
            """)
    else:
        st.warning("No matching company found.")
