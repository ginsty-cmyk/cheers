import os
import json
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# 存储房间数据: {room_id: {"total": 100, "bombs": [], "clicked": [], "found": 0, "conns": []}}
rooms = {}

class RoomConfig(BaseModel):
    total: int
    bomb_count: int

@app.get("/")
async def get():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.post("/api/create")
async def create_room(config: RoomConfig):
    room_id = str(random.randint(1000, 9999))
    while room_id in rooms:
        room_id = str(random.randint(1000, 9999))
    
    # 生成随机炸弹
    bombs = random.sample(range(1, config.total + 1), config.bomb_count)
    
    rooms[room_id] = {
        "total": config.total,
        "bombs": bombs,
        "clicked": [],
        "found": 0,
        "conns": []
    }
    return {"room_id": room_id}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    if room_id not in rooms:
        await websocket.close(code=1008)
        return

    room = rooms[room_id]
    room["conns"].append(websocket)
    
    # 初始数据同步
    await websocket.send_json({
        "type": "init",
        "total": room["total"],
        "clicked": room["clicked"],
        "found": room["found"]
    })

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg["type"] == "click":
                num = msg["num"]
                if num not in room["clicked"]:
                    room["clicked"].append(num)
                    is_bomb = num in room["bombs"]
                    if is_bomb:
                        room["found"] += 1
                    
                    # 广播
                    payload = json.dumps({
                        "type": "update",
                        "num": num,
                        "is_bomb": is_bomb,
                        "punish": room["found"] if is_bomb else 0
                    })
                    for conn in room["conns"]:
                        try:
                            await conn.send_text(payload)
                        except:
                            continue
    except WebSocketDisconnect:
        if websocket in room["conns"]:
            room["conns"].remove(websocket)

if __name__ == "__main__":
    # Zeabur 自动分配端口，默认 7860
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
