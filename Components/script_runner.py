import tempfile
import subprocess
import sys
import os
import base64
import shutil

class ScriptRunner:
    
    #รัน script พร้อมไฟล์แบบ in-memory โดยไม่รบกวนพื้นที่เครื่อง
    @staticmethod
    def run_script_with_memory_files(script_content, filename, files_dict):
        temp_dir = None
        original_cwd = os.getcwd()
        try:
            # สร้าง temp directory แยกต่างหาก
            temp_dir = tempfile.mkdtemp(prefix="script_runner_")
            
            # เปลี่ยน working directory ไป temp
            os.chdir(temp_dir)
            
            # สร้าง modified script ที่มีการสร้างไฟล์ชั่วคราว
            modified_script = ScriptRunner._create_modified_script_with_temp_dir(
                script_content, files_dict, temp_dir
            )
            
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False, 
                encoding='utf-8', dir=temp_dir
            ) as f:
                f.write(modified_script)
                temp_file_path = f.name
            
            result = subprocess.run(
                [sys.executable, temp_file_path],
                capture_output=True, 
                text=True, 
                timeout=60,
                cwd=temp_dir  # รันใน temp directory
            )
            
            # คืน working directory กลับ
            os.chdir(original_cwd)
            
            # ลบ script file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
            return result.stdout, result.stderr, result.returncode, temp_dir
            
        except subprocess.TimeoutExpired:
            if temp_dir and os.path.exists(temp_dir):
                os.chdir(original_cwd)
            return "", "Script execution timeout (60 seconds)", 1, temp_dir
        except Exception as e:
            if temp_dir and os.path.exists(temp_dir):
                os.chdir(original_cwd)
            return "", f"Error running script: {str(e)}", 1, temp_dir

    #รัน script แบบไม่มีไฟล์เพิ่มเติม
    @staticmethod
    def run_script(script_content, filename):
        temp_dir = None
        original_cwd = os.getcwd()
        try:
            temp_dir = tempfile.mkdtemp(prefix="script_runner_")
            os.chdir(temp_dir)
            
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False, 
                encoding='utf-8', dir=temp_dir
            ) as f:
                f.write(script_content)
                temp_file_path = f.name
                
            result = subprocess.run(
                [sys.executable, temp_file_path], 
                capture_output=True, text=True, timeout=60, cwd=temp_dir
            )
            
            os.chdir(original_cwd)
            os.unlink(temp_file_path)
            
            return result.stdout, result.stderr, result.returncode, temp_dir
        except subprocess.TimeoutExpired:
            if temp_dir and os.path.exists(temp_dir):
                os.chdir(original_cwd)
            return "", "Script execution timeout (60 seconds)", 1, temp_dir
        except Exception as e:
            if temp_dir and os.path.exists(temp_dir):
                os.chdir(original_cwd)
            return "", f"Error running script: {str(e)}", 1, temp_dir

#----------------------------------------------------------------------------------------------
    #หัวใจสำคัญที่ทำให้ script สามารถทำงานได้ใน temp directory
    @staticmethod
    def _create_modified_script_with_temp_dir(script_content, files_dict, temp_dir):
        
        file_creation_code = f"""
import tempfile
import os
import base64
import shutil

# กำหนด working directory เป็น temp
TEMP_DIR = r"{temp_dir}"
os.chdir(TEMP_DIR)

# สร้างไฟล์ชั่วคราวจาก imported files
_temp_files = {{}}
_text_files_data = {{}}
_binary_files_data = {{}}

"""
        
        # 1.แยกไฟล์ Text และ Binary
        for filename, content in files_dict.items():
            if content.startswith("__BINARY__"):
                binary_content = content[10:]
                file_creation_code += f'_binary_files_data["{filename}"] = "{binary_content}"\n'
            else:
                encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                file_creation_code += f'_text_files_data["{filename}"] = "{encoded_content}"\n'
        
        file_creation_code += """
# 2.สร้างไฟล์ Text ใน temp directory
for filename, encoded_content in _text_files_data.items():
    try:
        content = base64.b64decode(encoded_content).decode('utf-8')
    except UnicodeDecodeError:
        try:
            content = base64.b64decode(encoded_content).decode('tis-620')
        except:
            try:
                content = base64.b64decode(encoded_content).decode('cp874')
            except:
                content = base64.b64decode(encoded_content).decode('utf-8', errors='ignore')
    
    file_path = os.path.join(TEMP_DIR, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    _temp_files[filename] = file_path

# 3.สร้างไฟล์ Binary ใน temp directory
for filename, encoded_content in _binary_files_data.items():
    binary_data = base64.b64decode(encoded_content)
    file_path = os.path.join(TEMP_DIR, filename)
    with open(file_path, 'wb') as f:
        f.write(binary_data)
    _temp_files[filename] = file_path

# 4.Matplotlib Part
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Override plt.show() to save figures in temp directory
_original_show = plt.show
_figure_counter = 0

def _custom_show():
    global _figure_counter
    _figure_counter += 1
    filename = f"plot_{_figure_counter}.png"
    file_path = os.path.join(TEMP_DIR, filename)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved as: {filename}")
    plt.close()

plt.show = _custom_show

# 5.Pandas Part
import pandas as pd
_original_to_csv = pd.DataFrame.to_csv

def _custom_to_csv(self, path_or_buf=None, **kwargs):
    if path_or_buf and isinstance(path_or_buf, str):
        # ถ้าเป็น relative path ให้บันทึกใน temp directory
        if not os.path.isabs(path_or_buf):
            path_or_buf = os.path.join(TEMP_DIR, path_or_buf)
    return _original_to_csv(self, path_or_buf, **kwargs)

pd.DataFrame.to_csv = _custom_to_csv

# ===== Original Script Content =====
"""
        
        # แก้ไข encoding problems ใน script content
        script_content = script_content.replace("encoding='tis-620'", "encoding='utf-8'")
        
        # เพิ่ม original script
        modified_script = file_creation_code + script_content
        
        return modified_script
#----------------------------------------------------------------------------------------------