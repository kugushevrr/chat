from datetime import datetime
from aiohttp import web
from collections import deque
from os import environ
import asyncio
import aiohttp

routes = web.RouteTableDef()
websockets = set()
history = deque(maxlen=environ.get('MAX_HISTORY_ELEMENTS', 500))

@routes.get('/', name='index')
async def index(request):
    return web.FileResponse('./index.html')


@routes.post('/')
async def login(request):
    name = (await request.post()).get('name')
    
    if name:
        return web.HTTPFound(request.app.router['chat'].url_for(name=name))
        
    return web.HTTPFound(request.app.router['index'].url_for())


@routes.get('/{name}/', name='chat')
async def chat_page(request):
    with open('chat.html', 'rb') as f:
        return web.Response(body=f.read().decode('utf8'),content_type='text/html')


@routes.get('/{name}/ws/')
async def websocket(request):
    name = request.match_info['name']
    ws = web.WebSocketResponse(autoping=True, heartbeat=30)
    await ws.prepare(request)
    
    if name == 'system':
        return ws

    await send_to_all('system', f'{name} joined!')
    for text in history:
        await ws.send_str(text)
    websockets.add(ws)

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await send_to_all(name, msg.data)
    finally:
        await send_to_all('system', f'{name} left.')
        websockets.remove(ws)

    return ws


async def send_to_all(name, message):
    now = datetime.now()
    text = f'{now:%H:%M:%S} – {name}: {message}'
    history.append(text)
    asyncio.gather(*(asyncio.create_task(ws.send_str(text)) for ws in websockets))


def get_app():
    app = web.Application()
    app.add_routes(routes)
    return app

if __name__ == '__main__':
    app = get_app()
    web.run_app(app)
