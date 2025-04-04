import streamlit as st
import pandas as pd
import re
import unidecode
import io
import uuid
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
    st.title("🔍 Kiểm tra Trùng Dữ Liệu")
    
    uploaded_file = st.file_uploader("📂 Chọn file Excel", type=["xlsx"], key="check_duplicate_uploader")

    if uploaded_file is not None:
        try:
            df_new = pd.read_excel(uploaded_file, engine="openpyxl")
            st.session_state['data_fixed'] = df_new  # Lưu vào session
            
            st.subheader("📊 Dữ liệu đã tải lên")
            st.dataframe(df_new, use_container_width=True)

            # Cho phép người dùng chọn các cột để kiểm tra trùng lặp
            selected_columns = st.multiselect("🛠 Chọn cột kiểm tra trùng lặp:", df_new.columns)
            
            if selected_columns:
                df_duplicates = df_new[df_new.duplicated(subset=selected_columns, keep=False)].sort_values(by=selected_columns)
                
                if df_duplicates.empty:
                    st.success("✅ Không có dữ liệu trùng lặp.")
                else:
                    st.warning(f"⚠️ Tìm thấy {df_duplicates.shape[0]} dòng dữ liệu trùng lặp!")
                    st.write("### 🔄 Dữ liệu Trùng Lặp:")
                    st.dataframe(df_duplicates)

                    # Lọc dữ liệu trùng, giữ lại email có đuôi '@gmail.com'
                    if "Email" in df_new.columns:
                        df_gmail = df_duplicates[df_duplicates["Email"].str.endswith("@gmail.com", na=False)]
                        df_gmail = df_gmail.drop_duplicates(subset=selected_columns, keep="first")
                    else:
                        df_gmail = df_duplicates.drop_duplicates(subset=selected_columns, keep="first")

                    df_non_duplicates = df_new[~df_new.duplicated(subset=selected_columns, keep=False)]
                    df_cleaned = pd.concat([df_non_duplicates, df_gmail])

                    st.success(f"✅ Dữ liệu sau khi làm sạch: {df_cleaned.shape[0]} dòng.")
                    st.write("### ✨ Dữ liệu Sau Khi Làm Sạch:")
                    st.dataframe(df_cleaned)

                    # 🔹 Người dùng nhập số dòng mỗi file
                    chunk_size = st.number_input("📌 Nhập số dòng cho mỗi file nhỏ:", min_value=100, value=8000, step=100)
                    
                    # 🔹 Người dùng nhập tiền tố cho tên file
                    prefix = st.text_input("📌 Nhập tiền tố cho file tải xuống:", value="Output_file")

                    # Khi nhấn nút, chia file thành nhiều phần nhỏ
                    if st.button("✂️ Chia nhỏ và tải xuống"):
                        zip_buffer = io.BytesIO()
                        with pd.ExcelWriter(zip_buffer, engine="openpyxl") as writer:
                            file_list = []
                            for i, chunk in enumerate(range(0, df_cleaned.shape[0], chunk_size)):
                                df_chunk = df_cleaned.iloc[chunk: chunk + chunk_size]
                                file_name = f"{prefix}_{i+1}.xlsx"
                                file_list.append(file_name)
                                df_chunk.to_excel(writer, sheet_name=f"Part {i+1}", index=False)

                        zip_buffer.seek(0)
                        st.success("🎉 File đã sẵn sàng để tải xuống!")

                        # Danh sách file sẽ được tạo
                        st.write("📂 **Danh sách file sẽ tải xuống:**")
                        for file in file_list:
                            st.write(f"- {file}")

                        # Nút tải xuống
                        st.download_button(
                            label="📥 Tải xuống dữ liệu đã xử lý",
                            data=zip_buffer,
                            file_name=f"{prefix}_cleaned_data.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

        except Exception as e:
            st.error(f"❌ Lỗi khi đọc file: {e}")
# --- Navigation Tabs ở đầu trang ---
tabs = st.tabs(["Clean Email", "Check Data", "Check duplicate"])
with tabs[0]:
    clean_email_page()

with tabs[1]:
    Check_data()
with tabs[2]:
    check_duplicate()
    
