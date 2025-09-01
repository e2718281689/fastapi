# main.py
import os
import json
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.responses import FileResponse
from packaging import version as version_parser # 使用强大的 packaging 库进行版本比较

# --- 常量定义 ---
FILES_DIR = "static_files"
MAPPING_FILE = "mapping.json"
OTA_CONFIG_FILE = "ota_config.json" # 新增OTA配置文件

# --- FastAPI 应用实例 ---
app = FastAPI(
    title="ESP32 File & OTA Server",
    description="为嵌入式设备提供别名文件下载和OTA固件更新服务。"
)

# --- 别名文件下载 (原有功能) ---

def get_filename_from_alias(alias: str) -> str:
    """从 mapping.json 文件中查找别名对应的真实文件名。"""
    try:
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
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
    filename = get_filename_from_alias(alias)
    print(f"收到别名请求 '{alias}', 映射到文件: '{filename}'")

    file_path = os.path.join(FILES_DIR, filename)

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

# --- 新增 OTA 固件更新功能 ---

@app.get("/ota", tags=["OTA Update"])
async def ota_update(
    device_model: str = Query(..., description="请求更新的设备型号, e.g., 'esp32-s3-generic'"),
    current_version: str = Query(..., description="设备当前的固件版本号, e.g., '1.0.0'")
):
    """
    检查并提供固件更新。
    设备需提供其型号和当前版本号。
    - 如果有新版本，返回固件文件。
    - 如果已是最新版，返回 304 Not Modified。
    """
    print(f"收到来自设备 '{device_model}' 的OTA请求, 当前版本: '{current_version}'")
    
    # 1. 读取并解析 OTA 配置文件
    try:
        with open(OTA_CONFIG_FILE, 'r', encoding='utf-8') as f:
            ota_config = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"服务器配置错误: '{OTA_CONFIG_FILE}' 未找到。")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"服务器配置错误: '{OTA_CONFIG_FILE}' 格式无效。")

    # 2. 查找对应设备的更新信息
    device_info = ota_config.get(device_model)
    if not device_info:
        raise HTTPException(status_code=404, detail=f"未找到设备型号 '{device_model}' 的更新策略。")

    latest_version_str = device_info.get("latest_version")
    firmware_filename = device_info.get("filename")

    if not latest_version_str or not firmware_filename:
        raise HTTPException(status_code=500, detail=f"设备型号 '{device_model}' 的配置不完整。")

    # 3. 比较版本号
    # 使用 packaging.version 来安全、准确地比较语义化版本号
    # 例如 '2.0.1' > '1.10.0'
    client_version = version_parser.parse(current_version)
    latest_version = version_parser.parse(latest_version_str)

    if client_version >= latest_version:
        print(f"设备 '{device_model}' 版本 '{current_version}' 已是最新版。")
        return Response(status_code=304) # 304 Not Modified

    print(f"发现新版本 '{latest_version_str}' > '{current_version}'。准备发送更新...")

    # 4. 发送新固件文件
    file_path = os.path.join(FILES_DIR, firmware_filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"固件文件 '{firmware_filename}' 在服务器上未找到。")
    if os.path.commonprefix((os.path.realpath(file_path), os.path.realpath(FILES_DIR))) != os.path.realpath(FILES_DIR):
        raise HTTPException(status_code=403, detail="禁止访问")
    
    print(f"正在为 '{device_model}' 发送固件文件: {firmware_filename}")
    return FileResponse(
        path=file_path,
        media_type='application/octet-stream',
        filename=firmware_filename
    )


# --- 根路径 ---
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "欢迎使用文件和OTA更新服务器。"}

