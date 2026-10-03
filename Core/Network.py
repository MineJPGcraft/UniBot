import asyncio
from io import BytesIO

from httpx import AsyncClient

from Scripts.Logging import logger

client = AsyncClient(follow_redirects=True)

# GitHub 加速镜像列表（依次尝试，全部失败后回退到原始地址直连）
GITHUB_MIRRORS = [
    'https://ghproxy.net/',
    'https://gh-proxy.com/',
    'https://ghfast.top/',
    'https://ghproxy.cc/',
]

# 玩家头像 CDN 列表（按名字查询，依次尝试）
AVATAR_CDNS = [
    'https://minotar.net/avatar/{name}/{size}',
    'https://mc-heads.net/avatar/{name}/{size}',
]

# 头像尺寸：获取 48px 保证渲染清晰，模板中以 24px 展示
AVATAR_SIZE = 48
# 头像并发请求上限，避免同时请求过多触发 CDN 限流
MAX_AVATAR_CONCURRENCY = 10

# 玩家头像内存缓存：{(名字, 尺寸): (图片内容, Content-Type)}，避免重复请求外部 CDN
avatar_cache: dict[tuple[str, int], tuple[bytes, str]] = {}
MAX_AVATAR_CACHE = 100


async def request(url: str):
    try:
        response = await client.get(url)
        if response.status_code == 200:
            return response.json()
        logger.warning(f'Request to {url} failed: unexpected status code {response.status_code}')
    except Exception as error:
        logger.warning(f'Request to {url} failed: {error}')


async def post_request(url: str, payload: dict) -> dict | None:
    """发送 POST JSON 请求，成功返回响应 JSON，失败返回 None。"""
    try:
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        logger.warning(f'Request to {url} failed: unexpected status code {response.status_code}')
    except Exception as error:
        logger.warning(f'Request to {url} failed: {error}')
    return None


async def download(url: str) -> BytesIO | None:
    """下载单个 URL 的文件内容，成功返回 BytesIO，失败返回 None。"""
    try:
        download_bytes = BytesIO()
        async with client.stream('GET', url) as stream:
            if stream.status_code != 200:
                logger.warning(f'Download of {url} failed: unexpected status code {stream.status_code}')
                return
            async for chunk in stream.aiter_bytes():
                download_bytes.write(chunk)
        download_bytes.seek(0)
        return download_bytes
    except Exception as error:
        logger.warning(f'Download of {url} failed: {error}')
        return


async def github_download(url: str) -> BytesIO | None:
    """下载 GitHub 文件，依次尝试加速镜像，全部失败后回退到原始地址直连。"""
    candidate_urls = [mirror + url for mirror in GITHUB_MIRRORS]
    candidate_urls.append(url)
    for candidate_url in candidate_urls:
        if result := await download(candidate_url):
            return result
    return


async def fetch_player_avatar(name: str, size: int) -> tuple[bytes, str] | None:
    """获取玩家头像（带内存缓存），依次尝试多个头像 CDN，全部失败后回退到史蒂夫默认头像。"""
    cache_key = (name, size)
    if cache_key in avatar_cache:
        return avatar_cache[cache_key]
    for url_template in AVATAR_CDNS:
        url = url_template.format(name=name, size=size)
        result = await download(url)
        if isinstance(result, BytesIO):
            avatar = (result.getvalue(), 'image/png')
            avatar_cache[cache_key] = avatar
            if len(avatar_cache) > MAX_AVATAR_CACHE:
                avatar_cache.clear()
            return avatar
    # 全部 CDN 都失败时回退到史蒂夫默认头像（MHF_Steve 是 Mojang 经典账号，对应默认皮肤）
    if name != 'MHF_Steve':
        return await fetch_player_avatar('MHF_Steve', size)
    return None


async def fetch_player_avatars(player_names: list[str], size: int = AVATAR_SIZE) -> dict[str, tuple]:
    """并发获取多个玩家头像，返回 {玩家名: (图片内容, Content-Type)}，获取失败的玩家不在结果中。"""
    semaphore = asyncio.Semaphore(MAX_AVATAR_CONCURRENCY)

    async def fetch_one(player_name: str) -> tuple[str, tuple] | None:
        async with semaphore:
            result = await fetch_player_avatar(player_name, size)
        if result is None:
            return None
        return player_name, result

    results = await asyncio.gather(*(fetch_one(name) for name in set(player_names)))
    avatars = {}
    for item in results:
        if item is not None:
            player_name, avatar = item
            avatars[player_name] = avatar
    return avatars
