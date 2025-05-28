import streamlit as st
import pandas as pd
import sqlite3

st.title("📤 Upload Company Excel File")

# Connect to SQLite DB
conn = sqlite3.connect("company_data.db", check_same_thread=False)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS companies (
    CIN TEXT PRIMARY KEY,
    Name TEXT,
    State TEXT,
    Email TEXT
)
""")
conn.commit()

# Upload Excel file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    # Standardize and clean headers
    expected_columns = ['CIN', 'Name', 'State', 'Email']
    if df.shape[1] >= 4:
        if df.iloc[0].astype(str).str.upper().tolist()[:4] == [col.upper() for col in expected_columns]:
            df = df[1:]

    df.columns = expected_columns
    df = df.reset_index(drop=True)

    # Clean and normalize data
    df['CIN'] = df['CIN'].astype(str).str.strip()
    df['Name'] = df['Name'].astype(str).str.strip().str.lower()
    df['State'] = df['State'].astype(str).str.strip()
    df['Email'] = df['Email'].astype(str).str.strip()

    # Drop duplicate CINs
    df = df.drop_duplicates(subset="CIN")

    # OPTIONAL: Clear all existing records before upload
    cursor.execute("DELETE FROM companies")
    conn.commit()

    # Insert or replace data into DB
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO companies (CIN, Name, State, Email)
            VALUES (?, ?, ?, ?)
        """, (row['CIN'], row['Name'], row['State'], row['Email']))
    conn.commit()

    st.success(f"✅ {len(df)} companies uploaded and saved to database.")
    st.dataframe(df)

# Search functionality
st.markdown("---")
st.subheader("🔍 Search Company Info")

search_name = st.text_input("Enter full or partial company name").strip().lower()

if search_name:
    cursor.execute("""
        SELECT DISTINCT * FROM companies WHERE LOWER(Name) LIKE ?
    """, ('%' + search_name + '%',))
    results = cursor.fetchall()

    if results:
        st.success(f"Found {len(results)} result(s):")
        for cin, name, state, email in results:
            st.markdown(f"""
            **Company Name**: `{name}`  
            **CIN**: `{cin}`  
            **State**: `{state}`  
            **Email**: `{email}`  
            ---""")
    else:
        st.warning("No matching company found.")

# Optional: Show full DB contents for debugging
with st.expander("📋 View All Stored Companies (Debugging)"):
    df_all = pd.read_sql_query("SELECT * FROM companies", conn)
    st.dataframe(df_all)
