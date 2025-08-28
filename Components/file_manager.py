import streamlit as st
import pandas as pd
import base64
import os
import shutil
import zipfile
import io
from .config import BINARY_EXTENSIONS, LANGUAGE_MAP

class FileManager:
    
    #ดึงไฟล์จาก temp directory ทั้งหมด
    @staticmethod
    def get_files_from_temp_dir(temp_dir):
        if not temp_dir or not os.path.exists(temp_dir):
            return []
        
        files = []
        
        # ค้นหาไฟล์ในโฟลเดอร์หลัก
        for file_name in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file_name)
            if os.path.isfile(file_path):
                files.append(file_path)
            elif os.path.isdir(file_path):
                # ค้นหาไฟล์ในโฟลเดอร์ย่อย (เช่น radarPlot folder)
                for sub_file in os.listdir(file_path):
                    sub_file_path = os.path.join(file_path, sub_file)
                    if os.path.isfile(sub_file_path):
                        files.append(sub_file_path)
        
        return files

    #ลบไฟล์ชั่วคราวใน temp directory ทั้งหมด
    @staticmethod
    def cleanup_temp_dir(temp_dir):
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    #สร้างไฟล์ ZIP
    @staticmethod
    def create_zip_from_files(file_paths):
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    # ใช้เฉพาะชื่อไฟล์ (ไม่รวม path) ใน ZIP
                    arcname = os.path.basename(file_path)
                    zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    #Func ยกเลิกการเลือกไฟล์
    @staticmethod
    def clear_file_selection():
        st.session_state.clear_file_uploader = True
        # เพิ่ม uploader_key เพื่อสร้าง key ใหม่
        st.session_state.uploader_key += 1
        st.rerun()

    #Func ประมวลผลไฟล์ที่อัปโหลด
    @staticmethod
    def process_uploaded_file(uploaded_file, i, uploader_key):
        file_extension = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else 'unknown'
        
        if file_extension in BINARY_EXTENSIONS:
            FileManager._process_binary_file(uploaded_file, file_extension, i, uploader_key)
        else:
            FileManager._process_text_file(uploaded_file, file_extension, i, uploader_key)
    #ประมวลผลไฟล์ Binary
    @staticmethod
    def _process_binary_file(uploaded_file, file_extension, i, uploader_key):
        st.info(f"📁 **ไฟล์ Binary:** {uploaded_file.name} ({file_extension.upper()})")
        
        # แสดงผล Excel files
        if file_extension in ['xlsx', 'xls']:
            try:
                uploaded_file.seek(0)  # รีเซ็ต pointer
                df = pd.read_excel(uploaded_file)
                st.markdown("**👁️ ตัวอย่างข้อมูลใน Excel:**")
                st.dataframe(df.head(10), use_container_width=True)
                
                # แสดงข้อมูลเพิ่มเติม
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.metric("📊 จำนวนแถว", len(df))
                with col_info2:
                    st.metric("📊 จำนวนคอลัมน์", len(df.columns))
                
                st.markdown("**📋 ชื่อคอลัมน์:**")
                st.write(", ".join(df.columns.tolist()))
                
            except Exception as e:
                st.error(f"❌ ไม่สามารถอ่านไฟล์ Excel: {e}")
                st.warning("⚠️ ไฟล์นี้เป็น Binary file ไม่สามารถแสดงเนื้อหาได้")
        else:
            st.warning("⚠️ ไฟล์นี้เป็น Binary file ไม่สามารถแสดงเนื้อหาได้")
        
        # ปุ่มเก็บไฟล์ Binary ใน Memory
        if st.button("💾 เก็บไฟล์ใน Memory", type="secondary", key=f"save_binary_{i}_{uploader_key}"):
            uploaded_file.seek(0)  # รีเซ็ต pointer ก่อนอ่าน
            binary_content = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
            st.session_state.imported_files[uploaded_file.name] = f"__BINARY__{binary_content}"
            st.success(f"✅ เก็บไฟล์ {uploaded_file.name} (Binary) ใน Memory สำเร็จ!")

    #ประมวลผลไฟล์ Text
    @staticmethod
    def _process_text_file(uploaded_file, file_extension, i, uploader_key):
        try:
            content = uploaded_file.read().decode('utf-8')
            
            display_language = LANGUAGE_MAP.get(file_extension, 'text')
            
            st.markdown("**👁️ ตัวอย่างเนื้อหาไฟล์:**")
            # แสดงเฉพาะ 10 บรรทัดแรก
            preview_content = '\n'.join(content.split('\n')[:10])
            if len(content.split('\n')) > 10:
                preview_content += '\n... (แสดงเพียง 10 บรรทัดแรก)'
            
            st.code(preview_content, language=display_language)
                
            # ปุ่มเก็บไฟล์ Text ใน Memory
            if st.button("💾 เก็บไฟล์ใน Memory", type="secondary", key=f"save_text_{i}_{uploader_key}"):
                st.session_state.imported_files[uploaded_file.name] = content
                st.success(f"✅ เก็บไฟล์ {uploaded_file.name} ใน Memory สำเร็จ!")
                
        except UnicodeDecodeError:
            # ถ้าอ่านเป็น text ไม่ได้ ให้จัดเป็น Binary
            st.warning("⚠️ ไม่สามารถแสดงเนื้อหาไฟล์ได้ (ไฟล์เป็น Binary file)")
            st.info(f"📁 **ไฟล์ Binary:** {uploaded_file.name} ({file_extension.upper()})")
            
            # ปุ่มเก็บไฟล์ Binary ใน Memory
            if st.button("💾 เก็บไฟล์ใน Memory", type="secondary", key=f"save_binary_fallback_{i}_{uploader_key}"):
                uploaded_file.seek(0)
                binary_content = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
                st.session_state.imported_files[uploaded_file.name] = f"__BINARY__{binary_content}"
                st.success(f"✅ เก็บไฟล์ {uploaded_file.name} (Binary) ใน Memory สำเร็จ!")