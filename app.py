import streamlit as st
import pandas as pd
import re
import unidecode
import io
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
    uploaded_file = st.file_uploader("Chọn file Excel", type=["xlsx"])
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
def other_page():
    st.title("Other Page")
    st.write("Nội dung của trang khác sẽ được cập nhật sau.")

# --- Navigation Tabs ở đầu trang ---
tabs = st.tabs(["Clean Email", "Other Page"])

with tabs[0]:
    clean_email_page()

with tabs[1]:
    other_page()