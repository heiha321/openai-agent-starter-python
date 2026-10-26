"""
Agent Tools — 出行决策 Agent 的高德地图工具模块
=================================================

私有模块（文件名以下划线开头，不会被映射成路由）。

四个工具全部基于高德开放平台 Web 服务 API：
  - search_malls_nearby      周边商场检索（/v3/place/around）
  - search_brand_in_mall     核验某商场内是否有指定品牌门店（/v3/place/around + /v3/place/text）
  - get_distance             两点之间的距离与耗时（/v3/distance）
  - check_brands_in_malls    批量核验 + 排序（组合上面的能力）

所有密钥只从环境变量 AMAP_API_KEY 读取，代码中不出现任何真实 Key。
"""

import json
import math
import os
import time
from typing import Annotated

import requests
from agents import function_tool

AMAP_BASE = "https://restapi.amap.com/v3"
TIMEOUT = 8


# ========== 内部工具函数（非 tool，供 tool 复用） ==========
def _api_key() -> str:
    return (os.getenv("AMAP_API_KEY") or "").strip()


def _get(path: str, **params) -> dict:
    """调用高德接口，统一错误处理。"""
    key = _api_key()
    if not key:
        return {"_error": "缺少环境变量 AMAP_API_KEY，请先在 .env 中配置高德 Web 服务 Key"}
    params["key"] = key
    params.setdefault("output", "JSON")
    try:
        resp = requests.get(f"{AMAP_BASE}{path}", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {"_error": f"高德接口请求失败：{type(e).__name__}: {e}"}
    except ValueError:
        return {"_error": "高德接口返回了非 JSON 内容"}

    if str(data.get("status")) != "1":
        return {
            "_error": f"高德接口返回错误：{data.get('info')}（infocode={data.get('infocode')}）"
        }
    return data


def _parse_lnglat(text: str):
    """"116.33,39.87" → (116.33, 39.87)；不是坐标则返回 None。"""
    try:
        lng, lat = [float(x) for x in str(text).replace("，", ",").split(",")[:2]]
        return (lng, lat)
    except (ValueError, AttributeError, IndexError):
        return None


def _geocode(address: str):
    """地名 → (lng, lat, 规范化地址)。失败返回 (None, None, None)。"""
    coord = _parse_lnglat(address)
    if coord:
        return coord[0], coord[1], address
    data = _get("/geocode/geo", address=address)
    if data.get("_error"):
        return None, None, None
    geocodes = data.get("geocodes") or []
    if not geocodes:
        return None, None, None
    coord = _parse_lnglat(geocodes[0].get("location", ""))
    if not coord:
        return None, None, None
    return coord[0], coord[1], geocodes[0].get("formatted_address", address)


def _haversine_m(a, b) -> int:
    """两点球面距离（米）。"""
    lng1, lat1 = a
    lng2, lat2 = b
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return int(2 * r * math.asin(math.sqrt(h)))


def _short(text: str, limit: int = 60) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _find_mall_poi(mall_name: str, city: str = ""):
    """把商场名解析成 POI（优先购物类），返回 (name, address, (lng, lat), distance_hint)。"""
    params = {"keywords": mall_name, "types": "060100", "offset": 20, "page": 1}
    if city:
        params["city"] = city
        params["citylimit"] = "true"
    data = _get("/place/text", **params)
    pois = (data or {}).get("pois") or []
    if pois:
        poi = pois[0]
        coord = _parse_lnglat(poi.get("location", ""))
        if coord:
            return poi.get("name", mall_name), poi.get("address", ""), coord, poi.get("distance")
    # 退路：用地理编码定位
    lng, lat, addr = _geocode(f"{city}{mall_name}" if city else mall_name)
    if lng:
        return mall_name, addr, (lng, lat), None
    return None, None, None, None


# ========== Tool 1: 周边商场检索 ==========
@function_tool
def search_malls_nearby(
    location: Annotated[str, "起点位置，可以是地名（如“红莲南路地铁站”“北京西站”）或“经度,纬度”坐标"],
    radius_m: Annotated[int, "搜索半径，单位米，默认 3000"] = 3000,
    limit: Annotated[int, "最多返回多少个商场，默认 10"] = 10,
) -> str:
    """根据起点位置搜索周边商场，返回商场名称、地址、与起点的直线距离和坐标。

    返回值已按距离升序排列。当用户给出“我在XX附近”并要找商场时，先调用本工具。
    """
    lng, lat, formatted = _geocode(location)
    if lng is None:
        return json.dumps(
            {"error": f"无法定位起点位置“{location}”，请让用户提供更明确的地址或直接给经纬度"},
            ensure_ascii=False,
        )

    data = _get(
        "/place/around",
        location=f"{lng:.6f},{lat:.6f}",
        types="060100",  # 购物服务;商场（关键词 OR 语法会漏结果，改用类型检索）
        radius=max(200, min(int(radius_m), 50000)),
        offset=25,
        page=1,
        extensions="base",
    )
    if data.get("_error"):
        return json.dumps({"error": data["_error"]}, ensure_ascii=False)

    origin = (lng, lat)
    malls, seen = [], set()
    for poi in data.get("pois") or []:
        name = poi.get("name") or ""
        coord = _parse_lnglat(poi.get("location", ""))
        if not name or not coord or name in seen:
            continue
        seen.add(name)
        malls.append(
            {
                "name": name,
                "address": _short(poi.get("address") or "", 50),
                "distance_m": _haversine_m(origin, coord),
                "location": f"{coord[0]:.6f},{coord[1]:.6f}",
                "type": (poi.get("type") or "").split(";")[-1],
            }
        )

    malls.sort(key=lambda m: m["distance_m"])
    return json.dumps(
        {
            "origin": formatted,
            "origin_location": f"{lng:.6f},{lat:.6f}",
            "radius_m": radius_m,
            "malls": malls[: max(1, min(int(limit), 20))],
        },
        ensure_ascii=False,
    )


# ========== Tool 2: 核验商场内品牌门店 ==========
@function_tool
def search_brand_in_mall(
    mall: Annotated[str, "商场名称，如“龙湖北京丽泽天街”"],
    brand: Annotated[str, "要核验的品牌名称，如“倍轻松”“西町村屋”"],
    city: Annotated[str, "商场所在城市，如“北京”，留空则按名称匹配"] = "",
    radius_m: Annotated[int, "以商场为中心的判定半径，单位米，默认 400"] = 400,
) -> str:
    """核验某个商场内是否开有指定品牌的门店。

    返回 found（是否找到）、门店列表（含门店名、楼层/地址、距商场中心的距离）。
    用于回答“这个商场有没有某品牌”，不要凭印象猜测。
    """
    mall_name, mall_addr, mall_center, _ = _find_mall_poi(mall, city)
    if mall_center is None:
        return json.dumps(
            {"error": f"无法定位商场“{mall}”，请确认商场名称或补充城市"},
            ensure_ascii=False,
        )

    data = _get(
        "/place/around",
        location=f"{mall_center[0]:.6f},{mall_center[1]:.6f}",
        keywords=brand,
        radius=max(50, min(int(radius_m), 3000)),
        offset=10,
        page=1,
        sortrule="distance",
        extensions="base",
    )
    if data.get("_error"):
        return json.dumps({"error": data["_error"]}, ensure_ascii=False)

    stores = []
    for poi in data.get("pois") or []:
        coord = _parse_lnglat(poi.get("location", ""))
        if not coord:
            continue
        dist = _haversine_m(mall_center, coord)
        if dist > int(radius_m):
            continue
        stores.append(
            {
                "name": poi.get("name"),
                "address": _short(poi.get("address") or "", 60),
                "distance_from_mall_m": dist,
                "location": f"{coord[0]:.6f},{coord[1]:.6f}",
            }
        )

    stores.sort(key=lambda s: s["distance_from_mall_m"])
    return json.dumps(
        {
            "mall": {
                "name": mall_name,
                "address": _short(mall_addr or "", 60),
                "location": f"{mall_center[0]:.6f},{mall_center[1]:.6f}",
            },
            "brand": brand,
            "found": bool(stores),
            "stores": stores[:5],
            "note": "" if stores else f"在“{mall_name}”周边 {radius_m} 米内未检索到“{brand}”门店",
        },
        ensure_ascii=False,
    )


# ========== Tool 3: 两点距离 ==========
@function_tool
def get_distance(
    origin: Annotated[str, "起点，地名或“经度,纬度”"],
    destination: Annotated[str, "终点，地名或“经度,纬度”"],
    mode: Annotated[str, "出行方式：walking（步行，默认）或 driving（驾车）"] = "walking",
) -> str:
    """计算起点到终点的距离与预计耗时，用于比较“哪个更近”。

    返回 distance_m（米）、duration_min（分钟）以及出行方式；路线接口不可用时退回直线距离。
    """
    olng, olat, ofmt = _geocode(origin)
    dlng, dlat, dfmt = _geocode(destination)
    if olng is None or dlng is None:
        return json.dumps({"error": "起点或终点无法定位，请提供更明确的地址"}, ensure_ascii=False)

    o = f"{olng:.6f},{olat:.6f}"
    d = f"{dlng:.6f},{dlat:.6f}"
    straight = _haversine_m((olng, olat), (dlng, dlat))

    dist_type = "1" if str(mode).lower().startswith("driv") else "3"
    data = _get("/distance", origins=o, destination=d, type=dist_type)
    results = (data or {}).get("results") or []
    if results:
        item = results[0]
        distance_m = int(float(item.get("distance") or straight))
        duration_s = int(float(item.get("duration") or 0))
        return json.dumps(
            {
                "origin": ofmt,
                "destination": dfmt,
                "mode": "driving" if dist_type == "1" else "walking",
                "distance_m": distance_m,
                "duration_min": round(duration_s / 60, 1),
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "origin": ofmt,
            "destination": dfmt,
            "mode": "straight_line",
            "distance_m": straight,
            "duration_min": None,
            "note": "路线规划接口不可用，已返回直线距离",
        },
        ensure_ascii=False,
    )


# ========== Tool 4: 批量核验并排序 ==========
@function_tool
def check_brands_in_malls(
    location: Annotated[str, "用户起点位置，地名或“经度,纬度”，用于计算商场距离"],
    mall_names: Annotated[str, "候选商场名称，多个用逗号分隔"],
    brands: Annotated[str, "需要同时满足的品牌，多个用逗号分隔"],
    city: Annotated[str, "城市名，如“北京”，用于缩小商场定位范围"] = "",
) -> str:
    """批量核验多个商场是否同时拥有多个品牌，并按距离排序。

    返回每个商场的命中情况（hit_brands / missing_brands）、距离，以及满足全部品牌的首选商场。
    候选商场多于 3 个、或需要同时核验 2 个以上品牌时优先使用本工具。
    """
    names = [n.strip() for n in mall_names.replace("，", ",").split(",") if n.strip()]
    wanted = [b.strip() for b in brands.replace("，", ",").split(",") if b.strip()]
    if not names or not wanted:
        return json.dumps({"error": "mall_names 和 brands 都不能为空"}, ensure_ascii=False)

    olng, olat, ofmt = _geocode(location)
    if olng is None:
        return json.dumps({"error": f"无法定位起点“{location}”"}, ensure_ascii=False)

    rows = []
    for name in names[:10]:
        mall_name, mall_addr, mall_center, _ = _find_mall_poi(name, city)
        if mall_center is None:
            rows.append({"mall": name, "error": "无法定位该商场"})
            continue
        hit, missing, evidence = [], [], []
        for brand in wanted[:4]:
            data = _get(
                "/place/around",
                location=f"{mall_center[0]:.6f},{mall_center[1]:.6f}",
                keywords=brand,
                radius=400,
                offset=5,
                page=1,
                extensions="base",
            )
            # 高德个人 Key 的并发上限较低，命中限流时等待后重试一次
            if "LIMIT" in str(data.get("_error", "")):
                time.sleep(1.2)
                data = _get(
                    "/place/around",
                    location=f"{mall_center[0]:.6f},{mall_center[1]:.6f}",
                    keywords=brand,
                    radius=400,
                    offset=5,
                    page=1,
                    extensions="base",
                )
            time.sleep(0.2)  # 避免连续调用触发 QPS 限流
            pois = (data or {}).get("pois") or []
            if pois:
                poi = pois[0]
                hit.append(brand)
                evidence.append(
                    {
                        "brand": brand,
                        "store": poi.get("name"),
                        "address": _short(poi.get("address") or "", 50),
                    }
                )
            else:
                missing.append(brand)
        rows.append(
            {
                "mall": mall_name,
                "address": _short(mall_addr or "", 50),
                "distance_from_origin_m": _haversine_m((olng, olat), mall_center),
                "hit_brands": hit,
                "missing_brands": missing,
                "all_hit": len(missing) == 0,
                "evidence": evidence,
            }
        )

    ok = [r for r in rows if r.get("all_hit")]
    ok.sort(key=lambda r: r["distance_from_origin_m"])
    return json.dumps(
        {
            "origin": ofmt,
            "required_brands": wanted,
            "checked": len(rows),
            "best": ok[0]["mall"] if ok else None,
            "all_hit_malls": [r["mall"] for r in ok],
            "rows": rows,
        },
        ensure_ascii=False,
    )
