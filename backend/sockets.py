from typing import List
from fastapi import (FastAPI,
                     WebSocket,
                     WebSocketDisconnect)
from fastapi.responses import HTMLResponse
import asyncio


app = FastAPI()


class Auction:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self.current_bid = 0
        self.highest_bidder = None


    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await websocket.send_json({
            "message": "Hi. It`s auction!",
            "current_bid": self.current_bid,
            "highest_bidder": self.highest_bidder
        })

    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)


    async def broadcast(self, message: dict):
        for conn in self.active_connections:
            await conn.send_json(message)

    
    async def send_bid(self, websocket: WebSocket, bid: int):
        if bid > self.current_bid:
            self.current_bid = bid
            self.highest_bidder = websocket.client.port
            await self.broadcast({
                "message": f"Нова ставка = {bid}",
                "current_bid": self.current_bid,
                "highest_bidder": f"Юзер {websocket.client.port}"
            })
        else:
            await websocket.send_json({
                "message" : "Ставка не може бути меньше ніж поточна",
                "current_bid": self.current_bid
            })


auction = Auction()


@app.get("/")
async def get():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Аукціон</title>
    </head>
    <body>
        <h1>Ласкаво просимо на аукціон!</h1>
        <p>Введіть вашу ставку:</p>
        <input id="bid" type="number" min="1" placeholder="Ваша ставка">
        <button onclick="sendBid()">Зробити ставку</button>
        <h2 id="currentBid">Поточна ставка: 0</h2>
        <h3 id="highestBidder">Лідер: Ніхто</h3>
        <ul id="messages"></ul>

        <script>
            const ws = new WebSocket("ws://localhost:8000/ws/main_auc");
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.current_bid !== undefined) {
                    document.getElementById("currentBid").innerText = "Поточна ставка: " + data.current_bid;
                }
                if (data.highest_bidder !== undefined) {
                    document.getElementById("highestBidder").innerText = "Лідер: " + data.highest_bidder;
                }
                const messages = document.getElementById("messages");
                const li = document.createElement("li");
                li.innerText = data.message;
                messages.appendChild(li);
            };

            const sendBid = () => {
                const bid = document.getElementById("bid").value;
                ws.send(JSON.stringify({ action: "bid", value: parseInt(bid, 10) }));
            };
        </script>
    </body>
    </html>
    """)



@app.websocket("/ws/main_auc")
async def websocket_endpoint(websocket: WebSocket):
    await auction.connect(websocket)
    try: 
        while 1: # скорочуємо код як говорив діма
            data = await websocket.receive_json()
            if data.get("action") == "bid":
                await auction.send_bid(websocket, data.get("value"))
    except WebSocketDisconnect as we:
        await websocket.send_json({
            "info" : f"Connection closed for {we.reason}"
        })
        await websocket.close()
    except WebSocketDisconnect:
        print("Disconnected")