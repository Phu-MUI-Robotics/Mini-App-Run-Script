import streamlit as st
import pymongo as pm
import os
from datetime import datetime
import pandas as pd
import base64
from Components.config import init_page_config, load_css, load_mongodb_config, BINARY_EXTENSIONS
from Components.script_runner import ScriptRunner
from Components.file_manager import FileManager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ตั้งค่าหน้าเว็บและโหลด CSS
init_page_config()
load_css("style.css")

# โหลดการตั้งค่า MongoDB
config = load_mongodb_config()

# เชื่อมต่อ MongoDB
@st.cache_resource
def init_connection():
    mongo_url = os.getenv("MONGO_URL")
    return pm.MongoClient(mongo_url)

client = init_connection()
mongo_db_name = os.getenv("MONGO_DB_NAME")
mongo_collection_name = os.getenv("MONGO_COLLECTION_NAME")

if not mongo_db_name or not mongo_collection_name:
    st.error("Environment variables MONGO_DB_NAME or MONGO_COLLECTION_NAME are not set.")
    st.stop()

db = client[mongo_db_name]
collection = db[mongo_collection_name]

# Fetch scripts จาก MongoDB
@st.cache_data(ttl=30)
def get_data():
    try:
        scripts = list(collection.find({}, {"filename": 1, "uploaded_at": 1, "size": 1, "file_type": 1}))
        return scripts
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return []

# Initialize Session States
if 'refresh_counter' not in st.session_state:
    st.session_state.refresh_counter = 0
if 'imported_files' not in st.session_state:
    st.session_state.imported_files = {}
if 'clear_file_uploader' not in st.session_state:
    st.session_state.clear_file_uploader = False
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0
if 'script_error' not in st.session_state:
    st.session_state.script_error = None

# หน้าหลัก
st.title("🐍 Python Script Runner")
st.markdown("โปรแกรมอำนวยความสะดวกในการรันสคริปต์")
st.markdown("---")

scripts = get_data()

# ======= ส่วน Import Files =======
st.subheader("📤 Import Files")

st.markdown("")
st.markdown("📝 **วิธีการ Import ไฟล์ :**")
st.markdown("- ลากและวางไฟล์ลงในกล่องด้านล่าง (รองรับหลายไฟล์พร้อมกัน)")  
st.markdown("- หรือคลิกปุ่ม 'Browse files' เพื่อเลือกไฟล์")
st.markdown("- 👁️ ดูเนื้อหาไฟล์เพื่อ ReCheck อีกรอบ")
st.markdown("- 💾 **กดปุ่ม 'เก็บไฟล์ใน Memory' เพื่อเตรียมไฟล์สำหรับ run script**")

# ข้อมูลไฟล์ที่ scripts ต้องการ
with st.expander("📋 ไฟล์ที่ Scripts ต้องการ", expanded=False):
    st.markdown("""
    **processDataset.py ต้องการ :**
    - `raw.csv` - ข้อมูลดิบที่มี columns: s1-s8, Smell
    - `smell_Name.xlsx` - ไฟล์ Excel ที่มี mapping ระหว่าง Smell กับ Name
    
    **dendrogram_plot.py และ pcaPlotNormal.py ต้องการ :**
    - `average_smell_sensor_values.csv` - ข้อมูลสำหรับสร้าง Dendrogram และ PCA plot
    """)

st.markdown("")

# File uploader section
col_upload, col_cancel = st.columns([4, 1])

with col_upload:
    if st.session_state.clear_file_uploader:
        st.session_state.clear_file_uploader = False
        uploaded_files = st.file_uploader("เลือกไฟล์ที่ต้องการ Import :", 
                                          accept_multiple_files=True,
                                          key=f"import_files_{st.session_state.uploader_key}", 
                                          help="รองรับไฟล์ทุกประเภท (txt, py, json, html, css, js, md, csv, log, xlsx, xls, pdf, png, jpg)")
        st.info("✅ ยกเลิกการเลือกไฟล์แล้ว กรุณาเลือกไฟล์ใหม่")
    else:
        uploaded_files = st.file_uploader("เลือกไฟล์ที่ต้องการ Import :", 
                                          accept_multiple_files=True,
                                          key=f"import_files_{st.session_state.uploader_key}", 
                                          help="รองรับไฟล์ทุกประเภท (txt, py, json, html, css, js, md, csv, log, xlsx, xls, pdf, png, jpg)")

with col_cancel:
    st.markdown("&nbsp;")
    if st.button("❌ ยกเลิกการเลือกไฟล์", type="secondary", use_container_width=True):
        FileManager.clear_file_selection()

# Process uploaded files
if uploaded_files:
    st.success(f"✅ เลือกไฟล์แล้ว {len(uploaded_files)} ไฟล์")
    
    # แสดงสรุปไฟล์ทั้งหมด
    st.markdown("### 📊 สรุปไฟล์ที่เลือก:")
    
    file_data = []
    for uploaded_file in uploaded_files:
        file_extension = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else 'unknown'
        file_data.append({
            "📄 ชื่อไฟล์": uploaded_file.name,
            "📁 ประเภท": file_extension.upper(),
            "📏 ขนาด (bytes)": uploaded_file.size
        })
    
    df_files = pd.DataFrame(file_data)
    st.dataframe(df_files, use_container_width=True)
    
    # ประมวลผลแต่ละไฟล์
    st.markdown("---")
    st.markdown("### 📁 รายละเอียดไฟล์แต่ละไฟล์:")
    
    for i, uploaded_file in enumerate(uploaded_files):
        with st.expander(f"📄 {uploaded_file.name}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📏 File Size", f"{uploaded_file.size} bytes")
            with col2:
                file_extension = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else 'unknown'
                st.metric("📁 File Type", file_extension)
            with col3:
                st.metric("📄 File Name", uploaded_file.name)

            try:
                FileManager.process_uploaded_file(uploaded_file, i, st.session_state.uploader_key)
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
    
    # ปุ่มเก็บไฟล์ทั้งหมดพร้อมกัน
    st.markdown("---")
    
    if st.button("💾 เก็บไฟล์ทั้งหมดใน Memory", type="primary", use_container_width=True, key=f"save_all_{st.session_state.uploader_key}"):
        success_count = 0
        error_count = 0
        
        for uploaded_file in uploaded_files:
            try:
                file_extension = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else 'unknown'
                uploaded_file.seek(0)
                
                if file_extension in BINARY_EXTENSIONS:
                    binary_content = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
                    st.session_state.imported_files[uploaded_file.name] = f"__BINARY__{binary_content}"
                    success_count += 1
                else:
                    try:
                        content = uploaded_file.read().decode('utf-8')
                        st.session_state.imported_files[uploaded_file.name] = content
                        success_count += 1
                    except UnicodeDecodeError:
                        uploaded_file.seek(0)
                        binary_content = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
                        st.session_state.imported_files[uploaded_file.name] = f"__BINARY__{binary_content}"
                        success_count += 1
                        
            except Exception as e:
                error_count += 1
                st.error(f"❌ ไม่สามารถเก็บไฟล์ {uploaded_file.name}: {e}")
        
        if success_count > 0:
            st.success(f"✅ เก็บไฟล์สำเร็จ {success_count} ไฟล์")
        if error_count > 0:
            st.error(f"❌ เก็บไฟล์ไม่สำเร็จ {error_count} ไฟล์")

# แสดงไฟล์ใน Memory
if st.session_state.imported_files:
    st.markdown("---")
    st.subheader("💾 ไฟล์ใน Memory")
    
    with st.expander(f"📁 ไฟล์ทั้งหมด ({len(st.session_state.imported_files)} ไฟล์)", expanded=False):
        for filename, content in st.session_state.imported_files.items():
            if content.startswith("__BINARY__"):
                st.markdown(f"📄 **{filename}** (Binary file - {len(content)} characters)")
            else:
                st.markdown(f"📄 **{filename}** (Text file - {len(content)} characters)")
    
    if st.button("🗑️ ล้างไฟล์ทั้งหมดใน Memory", type="secondary", use_container_width=True):
        st.session_state.imported_files = {}
        st.success("✅ ล้างไฟล์ใน Memory แล้ว")
        st.rerun()

st.markdown("---")

# ======= ส่วนเลือกและรัน Scripts =======
if scripts: 
    st.subheader("📂 เลือก Scripts")
    
    st.markdown("")
    st.markdown("📝 **วิธีการ Run Script :**")
    st.markdown("- เลือก Script ที่ต้องการจะ run จาก dropdown ด้านล่าง")  
    st.markdown("- 👁️ ดูเนื้อหาไฟล์เพื่อ ReCheck อีกรอบ")
    st.markdown("- กดปุ่ม 'Run Script' เพื่อรันสคริปต์")
    st.markdown("- หากเกิดข้อผิดพลาด จะมีรายละเอียดแสดงด้านล่าง")
    st.markdown("- 📊 กราฟและรูปภาพที่สร้างจะแสดงด้านล่างโดยอัตโนมัติ")
    st.markdown("")
    
    script_options = ["..."] + [script['filename'] for script in scripts]

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("**เลือก Scripts ที่ต้องการ :**")
        selected_script = st.selectbox(
            "เลือกไฟล์",
            script_options,
            key=f"script_selector_{st.session_state.refresh_counter}",
            label_visibility="hidden"
        )

    with col2:
        st.markdown("&nbsp;")
        if st.button("🔄 Refresh", type="secondary", use_container_width=True):
            st.cache_data.clear()
            st.session_state.refresh_counter += 1
            if 'script_error' in st.session_state:
                st.session_state.script_error = None
            st.rerun()
    
    # แสดงรายละเอียดไฟล์และรัน script
    if selected_script and selected_script != "...":
        selected_script_data = next((s for s in scripts if s['filename'] == selected_script), None)
        
        if selected_script_data:
            st.markdown("---")
            st.subheader(f"📄 {selected_script}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📏 File Size", f"{selected_script_data.get('size', 'Unknown')} bytes")
            with col2:
                st.metric("📁 File Type", selected_script_data.get('file_type', 'Unknown'))
            with col3:
                upload_date = selected_script_data.get('uploaded_at', 'Unknown')
                if upload_date != 'Unknown':
                    st.metric("📅 Uploaded", upload_date.strftime('%Y-%m-%d'))
                else:
                    st.metric("📅 Uploaded", "Unknown")
        
        script_doc = collection.find_one({"filename": selected_script})
        if script_doc and 'content' in script_doc:
            with st.expander("👁️ ดูเนื้อหาไฟล์", expanded=False):
                st.code(script_doc['content'], language='python')
                
            st.markdown("---")
            
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                if st.button("🚀 Run Script", type="primary", use_container_width=True):
                    st.markdown("### 📊 Script Output")
                    
                    temp_dir = None
                    generated_files = []
                    
                    with st.spinner("กำลังรันสคริปต์..."):
                        # รัน script
                        if st.session_state.imported_files:
                            stdout, stderr, returncode, temp_dir = ScriptRunner.run_script_with_memory_files(
                                script_doc['content'], 
                                selected_script,
                                st.session_state.imported_files
                            )
                        else:
                            stdout, stderr, returncode, temp_dir = ScriptRunner.run_script(
                                script_doc['content'], 
                                selected_script
                            )
                        
                        if returncode == 0:
                            st.success("✅ รันสคริปต์สำเร็จ!")
                            st.session_state.script_error = None
                            
                            if stdout.strip():
                                st.subheader("📤 Output:")
                                with st.container():
                                    st.code(stdout, language='text')
                            
                            # ดึงไฟล์จาก temp directory
                            if temp_dir:
                                temp_files = FileManager.get_files_from_temp_dir(temp_dir)
                                
                                plot_files = [f for f in temp_files if f.endswith('.png') and ('plot_' in os.path.basename(f) or 'radar_chart_' in os.path.basename(f))]
                                csv_files = [f for f in temp_files if f.endswith('.csv')]
                                
                                # แสดง plots
                                if plot_files:
                                    st.subheader("📊 Generated Plots:")
                                    for plot_file in sorted(plot_files):
                                        generated_files.append(plot_file)
                                        with st.container():
                                            filename = os.path.basename(plot_file)
                                            if 'radar_chart_' in filename:
                                                caption = f"Radar Chart: {filename}"
                                            else:
                                                caption = f"Generated Plot: {filename}"
                                            st.image(plot_file, caption=caption, use_container_width=True)
                                
                                # แสดง CSV files
                                if csv_files:
                                    st.subheader("📄 Generated CSV Files:")
                                    for csv_file in csv_files:
                                        csv_filename = os.path.basename(csv_file)
                                        if csv_filename not in st.session_state.imported_files.keys():
                                            generated_files.append(csv_file)
                                            st.info(f"📊 Created: {csv_filename}")
                                            
                                            try:
                                                df_preview = pd.read_csv(csv_file)
                                                with st.expander(f"👁️ Preview: {csv_filename}", expanded=False):
                                                    st.dataframe(df_preview.head(10), use_container_width=True)
                                            except:
                                                pass
                                
                                # ส่วนดาวน์โหลด ZIP
                                if generated_files:
                                    st.markdown("---")
                                    st.subheader("📦 Download Generated Files")
                                    
                                    st.markdown("**ไฟล์ที่จะรวมใน ZIP:**")
                                    for file_path in generated_files:
                                        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                                        st.markdown(f"- 📄 `{os.path.basename(file_path)}` ({file_size} bytes)")
                                    
                                    try:
                                        zip_data = FileManager.create_zip_from_files(generated_files)
                                        
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        script_name = selected_script.replace('.py', '')
                                        zip_filename = f"{script_name}_output_{timestamp}.zip"
                                        
                                        st.download_button(
                                            label="📦 ดาวน์โหลดไฟล์ทั้งหมด (ZIP)",
                                            data=zip_data,
                                            file_name=zip_filename,
                                            mime="application/zip",
                                            type="primary",
                                            use_container_width=True
                                        )
                                        
                                        st.success(f"✅ พร้อมดาวน์โหลด! ไฟล์ ZIP จะมีชื่อ: `{zip_filename}`")
                                        
                                    except Exception as e:
                                        st.error(f"❌ เกิดข้อผิดพลาดในการสร้าง ZIP file: {e}")
                                
                                # ทำความสะอาด temp directory
                                FileManager.cleanup_temp_dir(temp_dir)
                            
                            if not stdout.strip() and not generated_files:
                                st.info("ไม่มี output จากสคริปต์")
                                
                        else:
                            st.error("❌ เกิดข้อผิดพลาดในการรันสคริปต์")
                            
                            if stderr.strip():
                                st.session_state.script_error = stderr
                            
                            # ทำความสะอาด temp directory แม้เกิด error
                            if temp_dir:
                                FileManager.cleanup_temp_dir(temp_dir)

            # แสดง Error ด้านล่าง
            if st.session_state.script_error:
                st.markdown("---")
                st.subheader("🚨 Error Details:")
                with st.container():
                    st.code(st.session_state.script_error, language='text', wrap_lines=True)

else:
    st.info("📭 ไม่พบไฟล์ในฐานข้อมูล")
    st.markdown("กรุณาอัพโหลดไฟล์ Python ก่อนใช้งาน")
            
st.markdown("---")
st.markdown("**ขอบคุณที่แวะเข้ามาใช้ Service ครับผม (Phu MUI Robotics) ❤️**")