import uvicorn
import os
import sys

# 确保项目根目录在 path 中
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("正在启动火灾监测系统...")
    print("访问地址: http://localhost:8000")
    # 注意: 在树莓派上部署时，reload应该设为False以提高性能
    uvicorn.run("web.main:app", host="0.0.0.0", port=8000, reload=True)
