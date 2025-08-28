# main.py
import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

FILES_DIR = "static_files"
MAPPING_FILE = "mapping.json"

app = FastAPI(
    title="ESP32 File Download Server with Alias",
    description="通过别名请求来为设备提供文件下载。"
)

def get_filename_from_alias(alias: str) -> str:
    """从 mapping.json 文件中查找别名对应的真实文件名。"""
    try:
        with open(MAPPING_FILE, 'r') as f:
            mapping = json.load(f)
        
        filename = mapping.get(alias)
        if not filename:
            raise HTTPException(status_code=404, detail=f"别名 '{alias}' 未在映射文件中找到。")
        
        return filename

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"服务器错误: 映射文件 '{MAPPING_FILE}' 未找到。")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"服务器错误: 映射文件 '{MAPPING_FILE}' 格式无效。")


@app.get("/request_file/{alias}", tags=["File Transfer"])
async def request_file_by_alias(alias: str):
    """
    根据提供的别名，从服务器下载对应的文件。

    - **alias**: 文件的别名 (例如, 'latest_firmware')
    """
    # 1. 从别名获取真实文件名
    filename = get_filename_from_alias(alias)
    print(f"收到别名请求 '{alias}', 映射到文件: '{filename}'")

    # 2. 构建文件的完整路径
    file_path = os.path.join(FILES_DIR, filename)

    # 3. 安全性检查和文件响应 (与之前相同)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"文件 '{filename}' 未在服务器上找到。")
    if os.path.commonprefix((os.path.realpath(file_path), os.path.realpath(FILES_DIR))) != os.path.realpath(FILES_DIR):
        raise HTTPException(status_code=403, detail="禁止访问")

    print(f"正在发送文件: {filename}")
    return FileResponse(
        path=file_path,
        media_type='application/octet-stream',
        filename=filename
    )

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "欢迎使用文件下载服务器。请访问 /request_file/<别名> 来下载文件。"}

