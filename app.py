import streamlit as st
import pandas as pd
import re
import unidecode
import io
import uuid
import zipfile
from io import BytesIO
st.set_page_config(page_title="Email Data Cleaner", layout="wide")
# Inject CSS để thay đổi màu nút download
st.markdown("""
    <style>
    /* Style nút download */
    div.stDownloadButton > button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px 20px;
        text-align: center;
        font-size: 16px;
        border-radius: 4px;
        cursor: pointer;
    }
    div.stDownloadButton > button:hover {
        background-color: #45a049;
    }
    /* Canh giữa bảng dữ liệu (dataframe và data_editor) */
    [data-testid="stDataFrameContainer"],
    [data-testid="stDataEditorContainer"] {
        margin-left: auto;
        margin-right: auto;
        width: 90%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Các hàm hỗ trợ xử lý email ---
def is_valid_email(email):
    """Kiểm tra định dạng email hợp lệ."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, str(email)))

def remove_accents(input_str):
    """Loại bỏ dấu tiếng Việt khỏi chuỗi."""
    return unidecode.unidecode(input_str)

def remove_invisible_chars(s):
    """Loại bỏ các ký tự ẩn (invisible characters) khỏi chuỗi."""
    return re.sub(r'[\u200B\u200C\u200D\uFEFF]', '', s)

def fix_domain(email):

    parts = email.split('@')
    if len(parts) != 2:
        return email
    local, domain = parts
    domain = domain.strip()
    domain_parts = domain.split('.')
    if len(domain_parts) == 3 and domain_parts[1].lower() == "vnn":
        domain = f"{domain_parts[0]}.{domain_parts[2]}"
    return f"{local}@{domain}"

def clean_and_normalize_email(email, company_name):

    if pd.isna(email) or not email.strip():
        clean_name = remove_accents(str(company_name).strip().replace(" ", "").lower())
        return f"{clean_name}@default.com"
    
    # Xóa các ký tự ẩn và khoảng trắng
    email_clean = remove_invisible_chars(email).strip()
    email_clean = re.sub(r'\s+', '', email_clean)
    
    # Nếu email nối liền nhau, tách bằng dấu phân cách ;, dấu phẩy hoặc dấu gạch chéo
    emails = re.split(r'[;,/]+', email_clean)
    candidate = emails[0] if emails else email_clean
    
    # Nếu candidate không hợp lệ, trích xuất email hợp lệ bằng regex
    if not is_valid_email(candidate):
        matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', candidate)
        if matches:
            candidate = matches[0]
    
    if is_valid_email(candidate):
        return fix_domain(candidate)
    
    # Nếu không tìm được email hợp lệ, tạo email mới từ tên công ty
    clean_name = remove_accents(str(company_name).strip().replace(" ", "").lower())
    return f"{clean_name}@default.com"

def clean_email_page():
    # --- Giao diện Streamlit ---
    st.title("Trang chỉnh sửa dữ liệu email !")
    st.write("Upload file Excel chứa dữ liệu liên hệ")

    # Upload file Excel
    uploaded_file = st.file_uploader("Chọn file Excel", type=["xlsx"], key="clean_email_uploader")
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file, engine="openpyxl")
        except Exception as e:
            st.error(f"Lỗi khi đọc file: {e}")
        else:
            # Đọc file Excel và loại bỏ các cột có tên bắt đầu bằng "Unnamed"
            df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
            
            # Thêm cột "email_original" chứa email ban đầu
            df["email_original"] = df["Email"]
            
            st.subheader("Dữ liệu ban đầu")
            st.dataframe(df.head())
            st.write("Tổng số dòng dữ liệu:", df.shape[0])
            # Tách dữ liệu: các dòng có email  hợp lệ (df_valid)
            df_valid = df[df["Email"].apply(is_valid_email)].copy()
            st.subheader("Các Email  hợp lệ ban đầu (df_valid)")
            st.dataframe(df_valid)
            st.write("Số lượng Email  hợp lệ:", df_valid.shape[0])
            # Tách dữ liệu: các dòng có email không hợp lệ (df_invalid)
            df_invalid = df[~df["Email"].apply(is_valid_email)].copy()
            st.subheader("Các Email không hợp lệ ban đầu (df_invalid)")
            st.dataframe(df_invalid[["email_original", "Email"]], use_container_width=True)
            st.write("Số lượng Email không hợp lệ:", df_invalid.shape[0])
            
            # Cho phép người dùng chọn sửa các email không hợp lệ
            if st.button("Sửa các Email không hợp lệ"):
                # Tạo df_invalid_fixed bằng cách sửa email theo hàm clean_and_normalize_email
                df_invalid_fixed = df_invalid.copy()
                df_invalid_fixed["email_fixed"] = df_invalid_fixed.apply(
                    lambda row: clean_and_normalize_email(row["Email"], row["Tên"]), axis=1
                )
                # Tạo bảng so sánh gồm 2 cột: email_original và email_fixed
                df_compare = df_invalid_fixed[["email_original", "email_fixed"]].copy()
                
                st.subheader("So sánh Email ban đầu và Email đã sửa")
                st.write("So sánh lại với dữ liệu ban đầu, bạn hoàn toàn có thể sửa đổi email_fixed nếu chưa đúng")
                # Hiển thị bảng so sánh và cho phép người dùng chỉnh sửa trực tiếp cột "email_fixed"
                df_edited = st.data_editor(df_compare, num_rows="dynamic", key="edited_df", use_container_width=True)
                
                # Sau khi chỉnh sửa, cập nhật lại df_invalid_fixed với giá trị từ df_edited
                df_invalid_fixed["email_fixed"] = df_edited["email_fixed"]
                # Cập nhật cột Email trong df_invalid_fixed từ cột email_fixed đã chỉnh sửa
                df_invalid_fixed["Email"] = df_invalid_fixed["email_fixed"]
                # Loại bỏ cột email_fixed để tránh trùng lặp
                df_invalid_fixed = df_invalid_fixed.drop(columns=["email_fixed"])
                
                # Cập nhật bảng dữ liệu toàn bộ đã sửa:
                # - df_valid: các dòng có email hợp lệ ban đầu
                df_valid = df[df["Email"].apply(is_valid_email)]
                # - Gộp lại df_valid và df_invalid_fixed
                df_fixed = pd.concat([df_valid, df_invalid_fixed], axis=0).sort_index()
                # Loại bỏ cột email_original khỏi df_fixed
                df_fixed = df_fixed.drop(columns=["email_original"])
                
                # Sử dụng placeholder để hiển thị bảng df_fixed và cập nhật ngay lập tức sau chỉnh sửa
                st.subheader("Toàn bộ dữ liệu đã chỉnh sửa")
                fixed_placeholder = st.empty()
                fixed_placeholder.dataframe(df_fixed, use_container_width=True)
                st.write("Tổng số dòng:", df_fixed.shape[0])
                
                # Nút download cho bảng so sánh đã chỉnh sửa
                towrite_compare = io.BytesIO()
                with pd.ExcelWriter(towrite_compare, engine="openpyxl") as writer:
                    df_edited.to_excel(writer, index=False)
                st.download_button(
                    label="Tải file so sánh (email_original vs email_fixed)",
                    data=towrite_compare.getvalue(),
                    file_name="Email_Comparison.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # Nút download cho toàn bộ dữ liệu đã sửa
                towrite_full = io.BytesIO()
                with pd.ExcelWriter(towrite_full, engine="openpyxl") as writer:
                    df_fixed.to_excel(writer, index=False)
                st.download_button(
                    label="Tải file toàn bộ dữ liệu đã sửa",
                    data=towrite_full.getvalue(),
                    file_name="FullData_Fixed.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
def get_duplicate_groups(df, column_name):
    """Lấy tất cả các nhóm có giá trị trùng lặp trong cột chỉ định."""
    if column_name not in df.columns:
        return pd.DataFrame()
    return df[df.duplicated(subset=[column_name], keep=False)]

def Check_data():
    st.title("Kiểm tra Data")
    uploaded_file = st.file_uploader("Chọn file Excel", type=["xlsx"], key="check_data_uploader")

    if uploaded_file is not None:
        try:
            df_new = pd.read_excel(uploaded_file, engine="openpyxl")
            st.session_state['data_fixed'] = df_new  # Lưu vào session
            st.subheader("Dữ liệu mới đã tải lên")
            st.dataframe(df_new, use_container_width=True)
        except Exception as e:
            st.error(f"Lỗi khi đọc file: {e}")
            return  

    if 'data_fixed' not in st.session_state:
        st.warning("Chưa có dữ liệu! Vui lòng tải file.")
        return
    
    df_new = st.session_state['data_fixed']
    df_new = df_new.loc[:, ~df_new.columns.str.startswith("Unnamed")]
    # Chọn cột để kiểm tra trùng lặp
    selected_column = st.selectbox("Chọn cột để kiểm tra trùng lặp:", df_new.columns, key="selected_column")

    # Kiểm tra trùng lặp & lưu kết quả vào session_state
    if st.button("Kiểm tra trùng lặp"):
        st.session_state['duplicate_df'] = get_duplicate_groups(df_new, selected_column)

    # Hiển thị kết quả nếu có
    if 'duplicate_df' in st.session_state and not st.session_state['duplicate_df'].empty:
        duplicate_df = st.session_state['duplicate_df']
        st.subheader(f"Dữ liệu trùng lặp trong cột '{selected_column}'")
        st.dataframe(duplicate_df, use_container_width=True)

        # Chọn giá trị cụ thể để lọc
        unique_values = duplicate_df[selected_column].dropna().astype(str).unique()
        selected_value = st.selectbox(f"Chọn giá trị trong '{selected_column}' để xem:", unique_values, key="selected_value")

        # Lọc dữ liệu theo giá trị được chọn
        filtered_df = duplicate_df[duplicate_df[selected_column].astype(str) == str(selected_value)]
        st.subheader(f"Dữ liệu trùng có '{selected_column} = {selected_value}'")
        st.dataframe(filtered_df, use_container_width=True)
    elif 'duplicate_df' in st.session_state:
        st.success(f"Không có dữ liệu trùng lặp trong cột {selected_column}.")

def check_duplicate():
    st.title("🔍 Kiểm tra & Xử lý Trùng Dữ Liệu")

    uploaded_file = st.file_uploader("📂 Chọn file Excel", type=["xlsx"], key="check_duplicate_uploader_unique")

    if uploaded_file is not None:
        try:
            df_new = pd.read_excel(uploaded_file, engine="openpyxl", dtype=str)
            st.session_state['data_fixed'] = df_new

            st.subheader("📊 Dữ liệu đã tải lên")
            df_new = df_new.loc[:, ~df_new.columns.str.startswith("Unnamed")]

            st.dataframe(df_new, use_container_width=True)

            selected_columns = st.multiselect("🛠 Chọn cột kiểm tra trùng lặp:", df_new.columns)
            sort_duplicates = st.checkbox("🔃 Sắp xếp dữ liệu trùng lặp lại gần nhau", value=False)

            if selected_columns:
                df_base = df_new.sort_values(by=selected_columns).reset_index(drop=True) if sort_duplicates else df_new

                # Tìm các dòng trùng lặp (giữ tất cả trùng)
                df_duplicates = df_base[df_base.duplicated(subset=selected_columns, keep=False)]

                st.write("### 🔍 Dữ liệu Trùng Lặp" + (" (Đã sắp xếp)" if sort_duplicates else ""))
                st.dataframe(df_duplicates)
                st.markdown("### ✨ Chọn cách giữ dòng:")
                method = st.radio(
                    "Cách xử lý dòng trùng:",
                    ["Giữ dòng đầu tiên", "Giữ dòng có Email @gmail.com", "So sánh theo cột cụ thể"],
                    key="duplicate_keep_method"
                )

                keep_option = "first"
                df_cleaned = pd.DataFrame()

                if method == "Giữ dòng đầu tiên":
                    df_cleaned = df_new.drop_duplicates(subset=selected_columns, keep="first")

                elif method == "Giữ dòng có Email @gmail.com":
                    df_duplicates = df_new[df_new.duplicated(subset=selected_columns, keep=False)]
                    df_gmail = df_duplicates[df_duplicates["Email"].str.endswith("@gmail.com", na=False)]
                    df_gmail = df_gmail.drop_duplicates(subset=selected_columns, keep="first")
                    df_non_duplicates = df_new[~df_new.duplicated(subset=selected_columns, keep=False)]
                    df_cleaned = pd.concat([df_non_duplicates, df_gmail])

                elif method == "So sánh theo cột cụ thể":
                    compare_column = st.selectbox("📊 Chọn cột để so sánh:", df_new.columns)
                    compare_type = st.radio("🧮 Giữ dòng có giá trị:", ["Lớn nhất", "Nhỏ nhất"], horizontal=True)

                    if compare_column and compare_type:
                        try:
                            # Ép kiểu cột về số (Int64 cho phép NaN)
                            df_new[compare_column] = pd.to_numeric(df_new[compare_column], errors='coerce').astype("Int64")

                            # Bỏ các dòng không thể so sánh
                            df_valid = df_new.dropna(subset=[compare_column])

                            # Lọc giữ dòng có giá trị lớn nhất hoặc nhỏ nhất theo nhóm
                            if compare_type == "Lớn nhất":
                                df_cleaned = df_valid.loc[df_valid.groupby(selected_columns)[compare_column].idxmax()]
                            else:
                                df_cleaned = df_valid.loc[df_valid.groupby(selected_columns)[compare_column].idxmin()]

                            st.success(f"✅ Đã giữ lại các dòng có {compare_column} {compare_type.lower()} theo nhóm {selected_columns}")
                            st.dataframe(df_cleaned)
                        except Exception as e:
                            st.error(f"❌ Lỗi: Không thể xử lý cột '{compare_column}': {e}")


                st.success(f"✅ Dữ liệu sau khi làm sạch: {df_cleaned.shape[0]} dòng.")
                st.dataframe(df_cleaned)

                chunk_size = st.number_input("📌 Nhập số dòng cho mỗi file nhỏ:", min_value=100, value=8000, step=100)
                prefix = st.text_input("📌 Nhập tiền tố cho tên file:", value="Output_file")

                if st.button("📥 Tải tất cả file chia nhỏ"):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                        for i, chunk_start in enumerate(range(0, df_cleaned.shape[0], chunk_size)):
                            df_chunk = df_cleaned.iloc[chunk_start: chunk_start + chunk_size]
                            excel_buffer = io.BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                                df_chunk.to_excel(writer, index=False)
                            excel_buffer.seek(0)
                            file_name = f"{prefix}_{i+1}.xlsx"
                            zip_file.writestr(file_name, excel_buffer.read())
                    zip_buffer.seek(0)
                    st.download_button(
                        label="📦 Tải toàn bộ file chia nhỏ (.zip)",
                        data=zip_buffer,
                        file_name=f"{prefix}_split_files.zip",
                        mime="application/zip"
                    )

        except Exception as e:
            st.error(f"❌ Đã xảy ra lỗi: {e}")
def merge_data():
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
            st.dataframe(df_result)

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
def split_data():
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
                df_result = df_result.fillna('')  # Thay NaN bằng chuỗi rỗng
                # df_result = df_result.replace('nan', '')  # Thay chuỗi 'nan' bằng chuỗi rỗng (nếu có)
                # df_result.fillna('', inplace=True)

                st.subheader("Kết quả sau khi chia nhỏ dữ liệu")
                st.dataframe(df_result)

                excel_data = convert_df_to_excel(df_result)
                st.download_button(
                    label="Download cleaned data",
                    data=excel_data,
                    file_name="split_result.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


def FillData():
    st.title("📝 Điền Dữ Liệu từ File B sang File A")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📂 File A (Cần điền dữ liệu)")
        file_a = st.file_uploader("Tải lên File A", type=["xlsx", "csv"], key="file_a_uploader")
    
    with col2:
        st.subheader("📂 File B (Nguồn dữ liệu)")
        file_b = st.file_uploader("Tải lên File B", type=["xlsx", "csv"], key="file_b_uploader")
    
    if file_a is not None and file_b is not None:
        try:
            # Đọc file A
            if file_a.name.endswith('.csv'):
                df_a = pd.read_csv(file_a)
            else:
                df_a = pd.read_excel(file_a, engine="openpyxl")
            
            # Đọc file B
            if file_b.name.endswith('.csv'):
                df_b = pd.read_csv(file_b)
            else:
                df_b = pd.read_excel(file_b, engine="openpyxl")
            
            # Loại bỏ cột Unnamed
            df_a = df_a.loc[:, ~df_a.columns.str.startswith("Unnamed")]
            df_b = df_b.loc[:, ~df_b.columns.str.startswith("Unnamed")]
            
            # Hiển thị preview
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Xem trước File A:**")
                st.dataframe(df_a.head(5))
                st.write(f"Tổng số dòng: {df_a.shape[0]}")
            
            with col2:
                st.write("**Xem trước File B:**")
                st.dataframe(df_b.head(5))
                st.write(f"Tổng số dòng: {df_b.shape[0]}")
            
            st.markdown("---")
            
            # Chọn cột kiểm tra chung
            st.subheader("🔍 Bước 1: Chọn cột để kiểm tra trùng khớp")
            col1, col2 = st.columns(2)
            
            with col1:
                check_col_a = st.selectbox(
                    "Cột kiểm tra ở File A:",
                    df_a.columns.tolist(),
                    key="check_col_a"
                )
            
            with col2:
                check_col_b = st.selectbox(
                    "Cột kiểm tra ở File B:",
                    df_b.columns.tolist(),
                    key="check_col_b"
                )
            
            # Chọn cột nguồn và đích
            st.subheader("📋 Bước 2: Chọn cột nguồn và cột đích")
            col1, col2 = st.columns(2)
            
            with col1:
                source_col_b = st.selectbox(
                    "Cột lấy dữ liệu từ File B:",
                    df_b.columns.tolist(),
                    key="source_col_b"
                )
            
            with col2:
                target_col_a = st.selectbox(
                    "Cột cần điền ở File A:",
                    df_a.columns.tolist(),
                    key="target_col_a"
                )
            
            # Tùy chọn xử lý
            st.subheader("⚙️ Bước 3: Tùy chọn xử lý")
            overwrite = st.checkbox(
                "Ghi đè dữ liệu đã có trong File A",
                value=False,
                help="Nếu bỏ chọn, chỉ điền vào các ô trống"
            )
            
            # Nút thực hiện
            if st.button("🚀 Thực hiện điền dữ liệu", type="primary"):
                # Tạo bản copy để xử lý
                df_result = df_a.copy()
                
                # Tạo dictionary mapping từ File B
                mapping_dict = df_b.set_index(check_col_b)[source_col_b].to_dict()
                
                # Đếm số dòng được điền
                filled_count = 0
                
                # Điền dữ liệu
                for idx, row in df_result.iterrows():
                    check_value = row[check_col_a]
                    
                    # Kiểm tra xem giá trị có trong mapping không
                    if check_value in mapping_dict:
                        # Nếu overwrite=True hoặc ô đích đang trống
                        if overwrite or pd.isna(row[target_col_a]) or str(row[target_col_a]).strip() == '':
                            df_result.at[idx, target_col_a] = mapping_dict[check_value]
                            filled_count += 1
                
                # Hiển thị kết quả
                st.success(f"✅ Đã điền {filled_count} dòng dữ liệu thành công!")
                
                st.subheader("📊 Kết quả sau khi điền dữ liệu")
                st.dataframe(df_result, use_container_width=True)
                
                # So sánh trước và sau
                with st.expander("🔍 Xem chi tiết các dòng đã được điền"):
                    comparison_cols = [check_col_a, target_col_a]
                    df_compare = pd.DataFrame({
                        f'{check_col_a}': df_result[check_col_a],
                        f'{target_col_a} (Trước)': df_a[target_col_a],
                        f'{target_col_a} (Sau)': df_result[target_col_a]
                    })
                    # Chỉ hiển thị các dòng có thay đổi
                    df_changed = df_compare[df_a[target_col_a].astype(str) != df_result[target_col_a].astype(str)]
                    st.dataframe(df_changed, use_container_width=True)
                    st.write(f"Tổng số dòng có thay đổi: {len(df_changed)}")
                
                # Nút tải xuống
                towrite = io.BytesIO()
                with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                    df_result.to_excel(writer, index=False, sheet_name="Result")
                
                st.download_button(
                    label="📥 Tải xuống File kết quả",
                    data=towrite.getvalue(),
                    file_name="FileA_Filled.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
        except Exception as e:
            st.error(f"❌ Đã xảy ra lỗi: {e}")
    else:
        st.info("👆 Vui lòng tải lên cả 2 file Excel (File A và File B) để bắt đầu")

# --- Navigation Tabs ở đầu trang ---
tabs = st.tabs(["Clean Email", "Check Data", "Check duplicate","Merge Data","Split Data", "Fill Data"])
with tabs[0]:
    clean_email_page()

with tabs[1]:
    Check_data()
with tabs[2]:
    check_duplicate()
with tabs[3]:
    merge_data()
with tabs[4]:
    split_data()
with tabs[5]:
    FillData()
    
