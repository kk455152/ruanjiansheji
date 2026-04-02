import json
import os

def save_to_file(payload):
    """
    [流程官 A 提供] 优化后的持久化逻辑
    功能：自动分拣文件、创建目录、异常捕获
    """
    try:
        # 1. 提取类型 (必须对应 API 文档中的 type)
        data_type = payload.get("type", "unknown")
        
        # 2. 规范化存储路径 (建议存放在 data 文件夹下)
        folder = "records"
        if not os.path.exists(folder):
            os.makedirs(folder)
            
        file_path = os.path.join(folder, f"db_{data_type}.json")
        
        # 3. 写入数据 (确保中文不乱码)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            
        return True, file_path
    except Exception as e:
        return False, str(e)

# 使用建议：C 只需要在原来的 callback 替换掉 open(...) 后的那几行即可。