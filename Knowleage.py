import requests
import os
import json

# Thông tin cấu hình được lấy từ biến môi trường
API_KEY = os.getenv("API_KEY")
EXPERT_ID = int(os.getenv("EXPERT_ID"))
ENDPOINT = "https://knowledge.alpha.insea.io/api/"

# Danh sách các link Google Sheet bạn muốn thêm làm nguồn kiến thức
gsheet_links = [
    "https://docs.google.com/spreadsheets/d/1NevWtNUFlror5h7_v4VbbPQbi1yIxN1xwFUHddr7Sx0/edit?gid=1036535472#gid=1036535472",
    "https://docs.google.com/spreadsheets/d/1kcZ-Z0PbE7Wcjr8H0KjXimuZ-JALup9jS54xyDzc-ik/edit?resourcekey=&gid=165160180#gid=165160180"
]

# Hàm thêm kiến thức từ link
def add_knowledge_link(expert_id, source_url, enable_sync=True, knowledge_id=None):
    """
    Thêm một mục kiến thức mới từ link URL hoặc cập nhật một mục đã có.
    API này hỗ trợ các link từ Confluence và Google Drive.
    """
    data = {
        "sourceURL": source_url,
        "enableSync": enable_sync
    }
    if knowledge_id:
        data["knowledgeId"] = knowledge_id
    
    response = requests.post(
        f"{ENDPOINT}experts/{expert_id}/knowledges/link",
        json=data,
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    return response

# Lặp qua danh sách link và gọi hàm cho từng link
for i, link in enumerate(gsheet_links):
    print(f"Uploading Link {i+1}...")
    try:
        link_response = add_knowledge_link(EXPERT_ID, link)
        link_response.raise_for_status()

        # In kết quả thành công
        print(f"Upload status for link {i+1}: {link_response.status_code}")
        print(link_response.json())
    except requests.exceptions.RequestException as e:
        print(f"An error occurred for link {i+1}: {e}")