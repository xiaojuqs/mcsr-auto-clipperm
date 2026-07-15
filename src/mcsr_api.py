"""MCSR Ranked API 客户端"""
import httpx

BASE_URL = "https://api.mcsrranked.com"


class McsrApiError(Exception):
    """MCSR API 错误"""
    pass


class McsrApiClient:
    """MCSR Ranked API 客户端"""

    def __init__(self, client: httpx.AsyncClient = None):
        self.client = client or httpx.AsyncClient(timeout=30.0)

    async def get_user_matches(self, username: str, count: int = 60, season: int = None, match_type: int = None) -> list:
        """获取用户比赛列表（只返回有 VOD 的比赛）

        Args:
            username: Minecraft 用户名
            count: 获取数量（支持超过60，自动分页）
            season: 赛季号
            match_type: 比赛类型（1=Casual, 2=Ranked, 3=Private, 4=Event）

        Returns:
            有 VOD 的比赛列表
        """
        all_matches = []
        before = None
        remaining = count

        while remaining > 0:
            page_size = min(remaining, 60)
            params = {"count": page_size, "excludeDecayed": "true"}
            if season:
                params["season"] = season
            if match_type:
                params["type"] = match_type
            if before:
                params["before"] = before

            response = await self.client.get(f"{BASE_URL}/users/{username}/matches", params=params)
            response.raise_for_status()
            data = response.json()

            if data["status"] != "success":
                raise McsrApiError(f"API Error: {data.get('data')}")

            matches = data["data"]
            if not matches:
                break

            # 只返回有 VOD 的比赛
            vod_matches = [m for m in matches if m.get("vod") and len(m["vod"]) > 0]
            all_matches.extend(vod_matches)

            # 更新分页游标
            before = matches[-1]["id"]
            remaining -= len(matches)

            # 如果返回的比赛数少于请求的数量，说明已经没有更多比赛了
            if len(matches) < page_size:
                break

        return all_matches

    async def get_match_detail(self, match_id: str) -> dict:
        """获取比赛详情（含时间线）

        Args:
            match_id: 比赛 ID

        Returns:
            比赛详情数据
        """
        response = await self.client.get(f"{BASE_URL}/matches/{match_id}")
        response.raise_for_status()
        data = response.json()

        if data["status"] != "success":
            raise McsrApiError(f"API Error: {data.get('data')}")

        return data["data"]

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
