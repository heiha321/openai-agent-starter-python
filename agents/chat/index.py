"""
Agent handler — EdgeOne Makers
========================================

The file path agents/chat/index.py is auto-mapped to **POST /chat**.
(EdgeOne Makers convention: directory name = route name, `index` is the default entry.)

`context` contract:
    context.request.body    — dict, request body
    context.request.signal  — asyncio.Event, set when /chat/stop is called
    context.conversation_id — conversation ID
    context.run_id          — run ID for this invocation
    context.store           — EdgeOne built-in store; provides openai_session() and friends
"""

from typing import Any, AsyncGenerator
import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, OpenAIChatCompletionsModel, Runner

from .._logger import create_logger
from .._tools import (
    check_brands_in_malls,
    get_distance,
    search_brand_in_mall,
    search_malls_nearby,
)


load_dotenv()

logger = create_logger("chat")


# ========== LLM Model ==========
llm_client = AsyncOpenAI(
    api_key=os.getenv("AI_GATEWAY_API_KEY"),
    base_url=os.getenv("AI_GATEWAY_BASE_URL"),
)

llm_model = OpenAIChatCompletionsModel(
    model=os.getenv("AI_GATEWAY_MODEL", "@makers/deepseek-v4-flash"),
    openai_client=llm_client,
)


# ========== Agent ==========
INSTRUCTIONS = """你是「出行决策 Agent」，一位基于高德地图真实数据帮用户挑选商场的出行顾问。

## 你要解决的问题
用户告诉你自己在哪，以及想去的品牌/店铺，你要找出「离得近、且能一次满足所有品牌」的商场，并给出推荐理由。

## 工作流程（必须按顺序执行）
1. 提取条件：起点位置 + 必须有的品牌。缺起点就问起点；缺品牌偏好就说明只能按距离推荐。
2. 调 search_malls_nearby 拿到周边候选商场（返回已按距离升序）。
3. 核验品牌：
   - 候选 ≤3 家：对每家商场分别调 search_brand_in_mall 逐个品牌核验；
   - 候选 >3 家或品牌 ≥2 个：直接调 check_brands_in_malls 批量核验并排序。
4. 判断：优先推荐「全部品牌都命中」且距离最近的商场；没有全部命中的，如实说明，并给出折中方案（例如某商场命中 A 品牌、另一家命中 B 品牌，各自距离多少）。
5. 需要精确步行距离或耗时时，调 get_distance 补充。

## 硬性规则
- 商场名称、门店名称、楼层、距离、坐标一律以工具返回为准，绝不编造或估计。
- 用户说的品牌名可能有同音错字（例如「西厅村屋」实际是「西町村屋」、「倍轻松」即 breo 倍轻松）。检索不到时，换成更可能的写法再查一次，并在回答里点明这个纠正。
- 工具报错（鉴权失败、无结果、接口超时）时，直接说明失败原因和受影响的结论，不要用假设的数据往下答。
- 不要输出任何 API Key、环境变量、接口原始 JSON 或调试信息。
- 地点、商场或品牌信息不足时主动追问，最多问一个最关键的问题。

## 回答格式
先给结论（推荐哪家、距离多少），再给依据（命中品牌与门店位置），最后给可选方案。用中文，控制在 250 字以内，条目式，不要堆砌接口细节。"""

agent = Agent(
    name="出行决策助手",
    instructions=INSTRUCTIONS,
    tools=[search_malls_nearby, search_brand_in_mall, get_distance, check_brands_in_malls],
    model=llm_model,
)


# ========== SSE Helper ==========
def sse_event(event: str, data: dict) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ========== Event Stream Generator ==========
async def _event_stream(
    message: str,
    session=None,
    cancel_signal: asyncio.Event | None = None,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE frames from the agent stream.

    Accepts cancel_signal to enable cancellation — when set,
    the loop breaks and the SDK releases its connection.
    """
    result = Runner.run_streamed(agent, input=message, session=session)

    async for event in result.stream_events():
        # Check cancel between each event
        if cancel_signal and cancel_signal.is_set():
            break

        # Raw token delta → push per-character
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            logger.log(f"[stream] text_delta: {repr(event.data.delta)}")
            yield sse_event("text_delta", {"delta": event.data.delta})

        # Semantic event → tool called
        elif event.type == "run_item_stream_event":
            if event.name == "tool_called":
                tool_name = (
                    getattr(event.item, "name", None)
                    or getattr(getattr(event.item, "raw_item", None), "name", None)
                )
                if tool_name:
                    logger.log(f"[stream] tool_called: {tool_name}")
                    yield sse_event("tool_called", {"tool": tool_name})


# ========== Core Handler ==========
async def handler(context: Any) -> AsyncGenerator[str, None]:
    """EdgeOne Makers entry point.

    Uses OpenAI Agents SDK session for automatic memory:
      - SDK calls session.get_items() to inject history
      - SDK calls session.add_items() to persist assistant replies and tool results
    """
    request = context.request
    body = request.body
    message = body.get("message") if isinstance(body, dict) else None

    if not message:
        yield sse_event("error", {"message": "'message' is required"})
        yield sse_event("done", {})
        return

    # Accept both camelCase (chat handler historical convention) and snake_case
    # (cloud-functions convention) as a body field name for the user id.
    raw_user_id = ""
    if isinstance(body, dict):
        raw_user_id = body.get("userId") or body.get("user_id") or ""
    user_id = str(raw_user_id).strip() or None

    # Session for memory persistence
    cid = context.conversation_id

    logger.log(f"[request] cid={cid}, uid={user_id or '-'}, message={message[:50]!r}")

    # Write a user-indexed copy of the user message ONLY on the first turn of
    # this conversation, so /conversations (which scans the
    # user_conversation_index prefix) can list this thread.
    #
    # Why first-turn-only:
    #   - The OpenAI Agents SDK Session adapter does NOT pass user_id when it
    #     persists turns, so without a user-indexed write the user index stays
    #     empty and list_conversations(user_id=...) returns [].
    #   - But the index lives at the (user_id, conversation_id) level — once
    #     a single message has been written under this user_id, the
    #     conversation is reachable. Writing a user-indexed copy on every turn
    #     just produces duplicates that downstream consumers have to dedupe
    #     (see cloud-functions/conversations/index.py and history/index.py)
    #     and surfaces a duplicated user message in OpenAI Agents SDK traces
    #     because the SDK's session.get_items() will re-feed it as input
    #     alongside the new `message` argument.
    #   - We therefore probe with get_messages(limit=1); if the conversation
    #     already has any record, the index is established and we skip.
    #
    # The /history route already filters by metadata.agent_sdk_session and
    # dedupes adjacent items, so the chat window stays clean either way —
    # but the trace dashboard shows raw SDK input, hence the visible doubling.
    body_keys_preview = list(body.keys()) if isinstance(body, dict) else None
    logger.log(
        f"[user-index] body keys={body_keys_preview!r} "
        f"raw_user_id={raw_user_id!r} normalized_user_id={user_id!r} cid={cid!r}"
    )
    if user_id and cid:
        try:
            existing = await context.store.get_messages(
                conversation_id=cid, limit=1
            )
            already_indexed = bool(existing)
        except Exception as e:
            # If the probe fails, fall through to writing — better to leave
            # a duplicate than to lose the user index entirely.
            logger.error(
                f"[user-index] probe failed: {type(e).__name__}: {e}; "
                f"will write user-index entry anyway"
            )
            already_indexed = False

        if already_indexed:
            logger.log(
                f"[user-index] SKIPPED user-index write: cid={cid} already has "
                f"messages, user index for user_id={user_id!r} is established"
            )
        else:
            try:
                # NOTE: the Python store.append_message() does NOT accept a
                # `message_id` kwarg (unlike the TS counterpart) — the SDK
                # auto-generates one. Passing it raises TypeError, which
                # silently kills the user-index write.
                msg_id = await context.store.append_message(
                    conversation_id=cid,
                    role="user",
                    content=message,
                    user_id=user_id,
                )
                logger.log(
                    f"[user-index] WROTE first-turn user-indexed message: cid={cid} "
                    f"user_id={user_id} msg_id={msg_id!r}"
                )
            except Exception as e:
                # Non-fatal — chat itself should keep working even if the
                # user-index write fails.
                logger.error(f"[user-index] FAILED to write user index: {type(e).__name__}: {e}")
    else:
        logger.log(
            f"[user-index] SKIPPED user-index write: user_id={user_id!r} cid={cid!r} "
            f"(both must be truthy to trigger the write — this is why "
            f"/conversations would return empty for this user)"
        )

    session = context.store.openai_session(cid) if cid else None

    # Cancel signal (asyncio.Event), set when /chat/stop is called
    cancel_signal = request.signal
    stopped = False

    try:
        async for frame in _event_stream(message, session, cancel_signal):
            if cancel_signal.is_set():
                stopped = True
                break
            yield frame
    except asyncio.CancelledError:
        stopped = True
        logger.log("[stream] cancelled")
    except Exception as e:
        logger.error(f"[stream] error: {type(e).__name__}: {e}")
        # Try to surface upstream HTTP error body (e.g. OpenAI SDK APIStatusError) to the TRACE panel
        detail: Any = str(e)
        status: Any = None
        response = getattr(e, "response", None)
        if response is not None:
            status = getattr(response, "status_code", None)
            try:
                body_text = response.text if hasattr(response, "text") else None
                if callable(body_text):
                    body_text = body_text()
                if body_text:
                    try:
                        detail = json.loads(body_text)
                    except (json.JSONDecodeError, ValueError, TypeError):
                        detail = body_text
            except Exception:
                pass
        body_attr = getattr(e, "body", None)
        if body_attr and detail == str(e):
            detail = body_attr
        yield sse_event("error", {
            "message": str(e),
            "errorType": type(e).__name__,
            "status": status,
            "detail": detail,
        })
    finally:
        yield sse_event("done", {"stopped": stopped})
