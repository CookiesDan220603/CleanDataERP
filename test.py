import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

def split_row_generic(row, columns):
    values_split = {col: str(row[col]).split('\n') for col in columns}
    max_len = max(len(v) for v in values_split.values())
    rows = []

    for i in range(max_len):
        new_row = row.copy()
        for col in columns:
            new_row[col] = values_split[col][i] if i < len(values_split[col]) else ''
        rows.append(new_row)
    return rows

def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    processed_data = output.getvalue()
    return processed_data

st.title("Split Multi-line Cells into Multiple Rows")

uploaded_file = st.file_uploader("Upload your Excel or CSV file", type=["xlsx", "csv"])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("Dữ liệu xem trước")
    st.dataframe(df)

    all_columns = df.columns.tolist()
    cols_to_split = st.multiselect("Chọn các dòng có dữ liệu cần chia nhỏ", options=all_columns)

    if st.button("Chia nhỏ dòng"):
        if not cols_to_split:
            st.warning("Vui lòng chọn ít nhất 1 dòng để chạy")
        else:
            new_rows = []
            for _, row in df.iterrows():
                new_rows.extend(split_row_generic(row, cols_to_split))

            df_result = pd.DataFrame(new_rows)
            df_result = df_result.replace({np.nan: '', 'nan': ''})
            df_result.fillna('', inplace=True)

            st.subheader("Kết quả sau khi chia nhỏ dữ liệu")
            st.dataframe(df_result)

            excel_data = convert_df_to_excel(df_result)
            st.download_button(
                label="Download cleaned data",
                data=excel_data,
                file_name="split_result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
