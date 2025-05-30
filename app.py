import streamlit as st
import pandas as pd
import pyodbc

# SQL Server connection config - update as needed
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-ECD3902\\SQLEXPRESS;"
    "DATABASE=companies;"
    "Trusted_Connection=yes;"
)
cursor = conn.cursor()

# Connection test
try:
    cursor.execute("SELECT 1")
    cursor.fetchone()
    st.success("✅ Connected to SQL Server successfully!")
except Exception as e:
    st.error(f"❌ Failed to connect to SQL Server: {e}")

# Create or alter table with correct NVARCHAR types
table_fix_sql = """
IF OBJECT_ID('dbo.companies', 'U') IS NOT NULL
BEGIN
    ALTER TABLE dbo.companies ALTER COLUMN CIN NVARCHAR(50) NOT NULL;
    ALTER TABLE dbo.companies ALTER COLUMN Name NVARCHAR(255) NULL;
    ALTER TABLE dbo.companies ALTER COLUMN State NVARCHAR(100) NULL;
    ALTER TABLE dbo.companies ALTER COLUMN Email NVARCHAR(255) NULL;
END
ELSE
BEGIN
    CREATE TABLE dbo.companies (
        CIN NVARCHAR(50) NOT NULL PRIMARY KEY,
        Name NVARCHAR(255) NULL,
        State NVARCHAR(100) NULL,
        Email NVARCHAR(255) NULL
    )
END
"""
cursor.execute(table_fix_sql)
conn.commit()

# Show how many records exist in the table
try:
    cursor.execute("SELECT COUNT(*) FROM dbo.companies")
    count = cursor.fetchone()[0]
    st.info(f"ℹ️ Companies table currently has {count} records.")
except Exception as e:
    st.warning(f"⚠️ Could not access companies table: {e}")

st.title("📤 Upload Company Excel File")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

BATCH_SIZE = 1000

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    expected_columns = ['CIN', 'Name', 'State', 'Email']
    if df.shape[1] >= 4:
        if df.iloc[0].astype(str).str.upper().tolist()[:4] == [col.upper() for col in expected_columns]:
            df = df[1:]

    df.columns = expected_columns
    df = df.reset_index(drop=True)

    df['CIN'] = df['CIN'].astype(str).str.strip().str.upper()
    df['Name'] = df['Name'].astype(str).str.strip().str.lower()
    df['State'] = df['State'].astype(str).str.strip()
    df['Email'] = df['Email'].astype(str).str.strip()
    df = df.drop_duplicates(subset="CIN")

    # Batch insert using MERGE
    for start in range(0, len(df), BATCH_SIZE):
        batch_df = df.iloc[start:start + BATCH_SIZE]
        for _, row in batch_df.iterrows():
            cursor.execute("""
                MERGE INTO dbo.companies AS target
                USING (SELECT ? AS CIN, ? AS Name, ? AS State, ? AS Email) AS source
                ON target.CIN = source.CIN
                WHEN MATCHED THEN
                    UPDATE SET Name = source.Name, State = source.State, Email = source.Email
                WHEN NOT MATCHED THEN
                    INSERT (CIN, Name, State, Email)
                    VALUES (source.CIN, source.Name, source.State, source.Email);
            """, (row['CIN'], row['Name'], row['State'], row['Email']))
        conn.commit()

    st.success(f"✅ {len(df)} companies uploaded and saved in batches of {BATCH_SIZE}.")
    st.dataframe(df)

st.markdown("---")
st.subheader("🔍 Search Company Info")

search_name = st.text_input("Enter full or partial company name").strip().lower()

if search_name:
    cursor.execute("""
        SELECT CIN, Name, State, Email FROM dbo.companies WHERE LOWER(Name) LIKE ?
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
---
""")
    else:
        st.warning("No matching company found.")

st.markdown("---")
with st.expander("📋 View All Stored Companies"):
    df_all = pd.read_sql("SELECT * FROM dbo.companies", conn)
    st.dataframe(df_all)

    # Export CSV
    csv_data = df_all.to_csv(index=False)
    st.download_button("Download as CSV", csv_data, "companies.csv", "text/csv")

    # Export JSON
    json_data = df_all.to_json(orient="records", indent=2)
    st.download_button("Download as JSON", json_data, "companies.json", "application/json")

    # Export SQL script (SQL Server compatible)
    def escape_sql(val):
        if isinstance(val, str):
            return val.replace("'", "''")
        return val

    def generate_sql_script(df):
        lines = [
            "IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='companies' AND xtype='U')",
            "CREATE TABLE dbo.companies (CIN NVARCHAR(50) PRIMARY KEY, Name NVARCHAR(255), State NVARCHAR(100), Email NVARCHAR(255));",
            "GO"
        ]
        for _, row in df.iterrows():
            lines.append(
                f"INSERT INTO dbo.companies (CIN, Name, State, Email) VALUES (N'{escape_sql(row['CIN'])}', N'{escape_sql(row['Name'])}', N'{escape_sql(row['State'])}', N'{escape_sql(row['Email'])}');"
            )
        lines.append("GO")
        return "\n".join(lines)

    sql_script = generate_sql_script(df_all)
    st.download_button("Download SQL Script", sql_script, "companies.sql", "text/sql")
