"""请求体解析工具：统一 JSON 对象请求体的读取与错误响应。"""

from fastapi import HTTPException, Request


async def parse_json_object(request: Request) -> dict:
    """解析 JSON 对象请求体，非法时抛 400（协议级错误）。"""
    try:
        body = await request.json()
    except Exception as error:
        raise HTTPException(status_code=400, detail='请求体必须是合法 JSON') from error
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail='请求体必须是 JSON 对象')
    return body
