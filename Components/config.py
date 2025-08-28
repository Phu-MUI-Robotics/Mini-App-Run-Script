import streamlit as st
import os
import yaml

def load_css(file_name):
    """โหลด CSS จากไฟล์แยก"""
    try:
        css_path = os.path.join(os.path.dirname(__file__), file_name)
        with open(css_path, 'r', encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"ไม่พบไฟล์ CSS: {file_name}")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลด CSS: {e}")

def load_mongodb_config():
    """โหลดการตั้งค่า MongoDB จาก YAML"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'mongodb_secret.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        st.error("ไม่พบไฟล์ mongodb_secret.yaml")
        st.stop()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลด config: {e}")
        st.stop()

def init_page_config():
    """ตั้งค่าหน้าเว็บ"""
    st.set_page_config(
        page_title="MUI Python Script Runner",
        page_icon="📝",
        layout="wide"
    )

# ค่าคงที่ต่างๆ
BINARY_EXTENSIONS = ['xlsx', 'xls', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'ico', 'zip', 'rar', '7z', 'exe', 'dll']

LANGUAGE_MAP = {
    'py': 'python',
    'js': 'javascript', 
    'html': 'html',
    'css': 'css',
    'json': 'json',
    'xml': 'xml',
    'sql': 'sql',
    'md': 'markdown',
    'txt': 'text',
    'csv': 'text',
    'log': 'text'
}