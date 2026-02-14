import cv2
import uvicorn
import time
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import sys
import os

# 添加项目根目录到Path以便导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fusion import DataFusionSystem

# 全局系统实例
fusion_system = DataFusionSystem()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时运行
    fusion_system.start()
    yield
    # 关闭时运行
    fusion_system.stop()

app = FastAPI(lifespan=lifespan)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
async def get_status():
    """获取当前系统状态API"""
    return JSONResponse(content=fusion_system.get_state(), headers={"Cache-Control": "no-store"})


@app.get("/api/llm")
async def llm_info():
    state = fusion_system.get_state()
    return JSONResponse(
        content={
            "mode": state.get("llm_mode"),
            "model": state.get("llm_model"),
            "use_image": state.get("llm_use_image"),
        },
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/analyze")
async def analyze_now():
    started = fusion_system.trigger_llm_analysis(trigger="manual")
    return JSONResponse(content={"started": started, "state": fusion_system.get_state()}, headers={"Cache-Control": "no-store"})


@app.get("/api/ollama")
async def ollama_status():
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        ok = sock.connect_ex(("127.0.0.1", 11434)) == 0
    finally:
        try:
            sock.close()
        except Exception:
            pass
    return JSONResponse(content={"ok": ok}, headers={"Cache-Control": "no-store"})

def generate_frames():
    """视频流生成器"""
    while True:
        frame = fusion_system.camera.get_frame()
        if frame is None:
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "No Camera Signal", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        else:
            detections = fusion_system.get_latest_detections()
            if isinstance(detections, list) and detections:
                frame = frame.copy()
                for d in detections[:20]:
                    try:
                        x1 = int(d.get("x1"))
                        y1 = int(d.get("y1"))
                        x2 = int(d.get("x2"))
                        y2 = int(d.get("y2"))
                        label = str(d.get("label", ""))
                        conf = float(d.get("confidence", 0))
                    except Exception:
                        continue

                    if label.lower() in ("fire", "flame"):
                        color = (0, 0, 255)
                    elif label.lower() == "smoke":
                        color = (0, 165, 255)
                    else:
                        color = (255, 128, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        frame,
                        f"{label} {conf:.2f}",
                        (x1, max(0, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        1,
                        cv2.LINE_AA,
                    )

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        if ret:
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.1)

@app.get("/video_feed")
async def video_feed():
    """视频流路由"""
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
