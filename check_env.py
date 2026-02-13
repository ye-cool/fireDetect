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

def check_camera():
    print("\n--- 检查摄像头设备 ---")
    
    # 1. 检查设备节点
    import glob
    devices = glob.glob("/dev/video*")
    if not devices:
        print("❌ 未检测到摄像头设备 (ls /dev/video* 为空)")
        print("   -> 请检查排线是否插反 (金属面应朝向 USB 接口侧)")
        print("   -> 尝试重启树莓派: sudo reboot")
        return False
    
    print(f"✅ 检测到视频设备: {', '.join(devices)}")
    
    # 2. 尝试读取
    import cv2
    print("ℹ️  尝试通过 OpenCV 读取...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("⚠️  无法通过默认后端 (index 0) 打开，尝试 V4L2...")
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✅ 摄像头读取成功! 分辨率: {frame.shape[1]}x{frame.shape[0]}")
            cap.release()
            return True
        else:
            print("❌ 摄像头已打开但无法获取帧 (读取失败)")
    else:
        print("❌ OpenCV 无法打开摄像头")
        print("   -> 可能是权限问题，尝试: sudo chmod 777 /dev/video*")
    
    return False

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
