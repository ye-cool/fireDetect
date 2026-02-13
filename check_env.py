import os
import sys
import importlib
import socket

def check_import(module_name, package_name=None):
    if package_name is None:
        package_name = module_name
    try:
        importlib.import_module(module_name)
        print(f"✅ 依赖库 {package_name} 已安装")
        return True
    except ImportError:
        print(f"❌ 缺少依赖库: {package_name}")
        return False

def check_directory(path):
    if os.path.isdir(path):
        print(f"✅ 目录 {path} 存在")
        return True
    else:
        print(f"❌ 关键目录缺失: {path}")
        return False

def check_ollama():
    # 简单的 Socket 连接检查
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 11434))
    if result == 0:
        print("✅ 本地 Ollama 服务正在运行 (端口 11434)")
        return True
    else:
        print("⚠️  本地 Ollama 服务未运行 (如果是云端模式请忽略)")
        return False
    sock.close()

def main():
    print("=== 开始系统环境自检 ===\n")
    
    all_pass = True
    
    # 1. 检查 Python 版本
    py_ver = sys.version_info
    print(f"ℹ️  Python 版本: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver.major < 3 or (py_ver.major == 3 and py_ver.minor < 8):
        print("❌ Python 版本过低，建议使用 Python 3.9+")
        all_pass = False

    print("\n--- 检查依赖库 ---")
    libs = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("jinja2", "jinja2"),
        ("cv2", "opencv-python"),
        ("openai", "openai"),
        ("dotenv", "python-dotenv"),
        ("pydantic", "pydantic")
    ]
    
    for mod, pkg in libs:
        if not check_import(mod, pkg):
            all_pass = False

    print("\n--- 检查项目结构 ---")
    dirs = ["core", "hardware", "web", "static", "templates"]
    for d in dirs:
        if not check_directory(d):
            all_pass = False

    print("\n--- 检查 AI 服务 ---")
    check_ollama()

    print("\n" + "="*30)
    if all_pass:
        print("🎉 环境检查通过！你可以运行系统了：")
        print("   python run.py")
    else:
        print("🚫 环境检查未通过，请先修复上述错误（通常是 pip install -r requirements.txt）")

if __name__ == "__main__":
    main()
