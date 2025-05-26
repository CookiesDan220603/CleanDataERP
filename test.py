import streamlit as st
import pandas as pd
from io import BytesIO

st.title("🔄 Gộp thông tin theo khối trong DataFrame")

# Upload file
uploaded_file = st.file_uploader("📂 Tải lên file Excel hoặc CSV", type=["csv", "xlsx"])

if uploaded_file:
    # Đọc file
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("📋 Xem trước dữ liệu")
    st.dataframe(df.head(10))

    # Chọn cột X (bắt đầu block) và Y (gom dữ liệu)
    x_col = st.selectbox("🧱 Chọn cột để xác định khối (X)", df.columns)
    y_col = st.selectbox("📍 Chọn cột để gom thông tin (Y)", df.columns)

    if st.button("🚀 Thực hiện gom dữ liệu"):
        # Tìm chỉ số bắt đầu block
        block_start_indices = df[df[x_col].notna()].index.tolist()
        block_start_indices.append(len(df))  # Đảm bảo chặn cuối

        rows_to_drop = set()

        for i in range(len(block_start_indices) - 1):
            start = block_start_indices[i]
            end = block_start_indices[i + 1]
            block = df.loc[start:end-1]

            # Gom dữ liệu cột Y
            values = (
                block[y_col]
                .dropna()
                .astype(str)
                .str.strip()
                .loc[lambda x: x != '']
                .unique()
                .tolist()
            )

            value_string = ",".join(values)
            df.at[start, y_col] = value_string

            # Xoá các dòng chỉ có giá trị Y (có thể điều chỉnh logic này tùy bạn)
            idx_range = df.index[(df.index > start) & (df.index < end)]
            for j in idx_range:
                if (
                    pd.isna(df.at[j, x_col]) and
                    df.at[j, y_col] in values and
                    all(pd.isna(df.at[j, col]) for col in df.columns if col not in [y_col])
                ):
                    rows_to_drop.add(j)

        df_result = df.drop(index=list(rows_to_drop)).reset_index(drop=True)

        st.success("✅ Hoàn tất xử lý!")
        st.dataframe(df_result.head(20))

        # Xuất file
        def convert_df(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Sheet1")
            return output.getvalue()

        excel_bytes = convert_df(df_result)
        st.download_button(
            label="⬇️ Tải xuống kết quả",
            data=excel_bytes,
            file_name="ket_qua_gom.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
