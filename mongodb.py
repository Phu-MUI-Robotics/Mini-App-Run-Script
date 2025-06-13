import pymongo as pm
import os
from datetime import datetime

# Connect to MongoDB
client = pm.MongoClient(os.getenv("MONGO_URL", "mongodb+srv://phurissomkaew:h8SKdTGxl4QscIEK@newclusterphu.ieissvx.mongodb.net"))
db = client.db01
collection = db.RunScript

#เก็บไฟล์ไหนให้ปรับตรงนี้
files_to_store = [
    "dendrogram_plot.py",
    "pcaPlotNormal.py", 
    "processDataset.py"
]

#Path เก็บไฟล์
download_path = "D:/MUI-Robotics/PythonScript-สำหรับทำMiniApp"

# ตรวจสอบว่า directory
if not os.path.exists(download_path):
    print(f"Directory not found: {download_path}")
    exit()

print(f"Looking for files in: {download_path}")

#-----------------------------------------------------------------------------------------
for file_name in files_to_store:
    filepath = os.path.join(download_path, file_name)
    print(f"Checking file: {filepath}")
    
        
    if os.path.exists(filepath):
        # เช็คว่าไฟล์มีอยู่ในฐานข้อมูลแล้วหรือไม่
        existing_file = collection.find_one({"filename": file_name})
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        document = {
            "filename": file_name,
            "content": content,
            "file_type": "python",
            "uploaded_at": datetime.now(),
            "size": os.path.getsize(filepath)
        }
        
        if existing_file:
            # อัพเดทไฟล์ที่มีอยู่
            result = collection.update_one(
                {"filename": file_name}, 
                {"$set": document}
            )
            print(f"🔄 Updated {file_name} (Modified {result.modified_count} document)")
        else:
            # เพิ่มไฟล์ใหม่
            result = collection.insert_one(document)
            print(f"✅ Stored {file_name} with ID: {result.inserted_id}")
    else:
        print(f"❌ File {file_name} not found at {filepath}")

# แสดงไฟล์ที่มีอยู่ใน directory
print("\nFiles in directory:")
try:
    for file in os.listdir(download_path):
        if file.endswith('.py'):
            print(f"  - {file}")
except Exception as e:
    print(f"Error listing directory: {e}")