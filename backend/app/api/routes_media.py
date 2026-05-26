import json
from collections.abc import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.media import MediaItem, MediaStatus, ParsedResult, RenamePlan, TmdbMatch
from app.schemas.media import (
    MediaItemRead,
    ParsedResultRead,
    RenamePlanRead,
    RenamePlanRequest,
    ScanRequest,
    SelectMatchRequest,
    TmdbMatchRead,
)
from app.services.file_ops import FileOperationService
from app.services.llm_parser import LLMParserService
from app.services.rename_planner import RenamePlannerService
from app.services.scanner import ScannerService
from app.services.tmdb import TMDBService

router = APIRouter(prefix="/media-items", tags=["media"])


@router.post("/scan", response_model=list[MediaItemRead])
def scan(payload: ScanRequest, session: Session = Depends(get_session)) -> list[MediaItem]:
    try:
        return ScannerService(session).scan(payload.path, payload.recursive)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[MediaItemRead])
def list_media_items(session: Session = Depends(get_session)) -> list[MediaItem]:
    return list(session.exec(select(MediaItem).order_by(desc("created_at"))).all())


@router.get("/{item_id}", response_model=MediaItemRead)
def get_media_item(item_id: int, session: Session = Depends(get_session)) -> MediaItem:
    item = session.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="资源不存在")
    return item


@router.post("/{item_id}/parse", response_model=ParsedResultRead)
async def parse_media_item(item_id: int, session: Session = Depends(get_session)) -> ParsedResult:
    item = session.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="资源不存在")
    parsed = await LLMParserService(session).parse(item)
    item.media_type = parsed.media_type
    item.status = MediaStatus.PARSED
    session.add(parsed)
    session.add(item)
    session.commit()
    session.refresh(parsed)
    return parsed


def stream_event(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/{item_id}/parse-stream")
def parse_media_item_stream(item_id: int, session: Session = Depends(get_session)) -> StreamingResponse:
    item = session.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="资源不存在")
    parser = LLMParserService(session)

    async def event_generator() -> AsyncGenerator[str, None]:
        content = ""
        if not parser.can_use_llm():
            parsed = await parser.parse(item)
            item.media_type = parsed.media_type
            item.status = MediaStatus.PARSED
            session.add(parsed)
            session.add(item)
            session.commit()
            session.refresh(parsed)
            yield stream_event("fallback", {"message": "未配置 LLM，已使用规则解析"})
            yield stream_event("result", ParsedResultRead.model_validate(parsed).model_dump(mode="json"))
            yield stream_event("done", {"ok": True})
            return

        try:
            yield stream_event("start", {"message": "开始调用 LLM"})
            async for chunk in parser.stream_llm_content(item):
                content += chunk
                yield stream_event("delta", {"content": chunk})
            parsed = parser.normalize_llm_content(content, item)
            item.media_type = parsed.media_type
            item.status = MediaStatus.PARSED
            session.add(parsed)
            session.add(item)
            session.commit()
            session.refresh(parsed)
            yield stream_event("result", ParsedResultRead.model_validate(parsed).model_dump(mode="json"))
            yield stream_event("done", {"ok": True})
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError) as exc:
            session.rollback()
            yield stream_event("error", {"message": str(exc), "raw_content": content})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{item_id}/parsed", response_model=list[ParsedResultRead])
def list_parsed_results(item_id: int, session: Session = Depends(get_session)) -> list[ParsedResult]:
    return list(
        session.exec(
            select(ParsedResult)
            .where(ParsedResult.media_item_id == item_id)
            .order_by(desc("created_at"))
        ).all()
    )


@router.post("/{item_id}/match", response_model=list[TmdbMatchRead])
async def match_media_item(item_id: int, session: Session = Depends(get_session)) -> list[TmdbMatch]:
    item = session.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="资源不存在")
    parsed = session.exec(
        select(ParsedResult)
        .where(ParsedResult.media_item_id == item_id)
        .order_by(desc("created_at"))
    ).first()
    if not parsed:
        raise HTTPException(status_code=400, detail="请先解析资源")

    query_title = getattr(parsed, "title", None) or getattr(item, "filename", None) or str(item_id)
    try:
        matches = await TMDBService(session).search(item_id, parsed)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        response_text = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(
            status_code=status_code if status_code < 500 else 502,
            detail=f"TMDB 请求失败（HTTP {status_code}）：{response_text}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"TMDB 网络错误：{exc}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"TMDB 请求失败：{exc}") from exc

    if not matches:
        raise HTTPException(status_code=404, detail=f"TMDB 未搜索到结果，当前查询标题：{query_title}")

    for match in matches:
        session.add(match)
    item.status = MediaStatus.MATCHED if matches[0].score >= 0.9 else MediaStatus.NEEDS_REVIEW
    session.add(item)
    session.commit()
    return matches


@router.get("/{item_id}/matches", response_model=list[TmdbMatchRead])
def list_matches(item_id: int, session: Session = Depends(get_session)) -> list[TmdbMatch]:
    return list(
        session.exec(
            select(TmdbMatch)
            .where(TmdbMatch.media_item_id == item_id)
            .order_by(desc("score"))
        ).all()
    )


@router.post("/{item_id}/select-match", response_model=TmdbMatchRead)
def select_match(
    item_id: int,
    payload: SelectMatchRequest,
    session: Session = Depends(get_session),
) -> TmdbMatch:
    item = session.get(MediaItem, item_id)
    match = session.get(TmdbMatch, payload.match_id)
    if not item or not match or match.media_item_id != item_id:
        raise HTTPException(status_code=404, detail="匹配不存在")
    matches = session.exec(select(TmdbMatch).where(TmdbMatch.media_item_id == item_id)).all()
    for row in matches:
        row.selected = row.id == payload.match_id
        session.add(row)
    item.status = MediaStatus.MATCHED
    session.add(item)
    session.commit()
    session.refresh(match)
    return match


@router.post("/{item_id}/rename-plan", response_model=RenamePlanRead)
def create_rename_plan(
    item_id: int,
    payload: RenamePlanRequest,
    session: Session = Depends(get_session),
) -> RenamePlan:
    item = session.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="资源不存在")
    parsed = session.exec(
        select(ParsedResult)
        .where(ParsedResult.media_item_id == item_id)
        .order_by(desc("created_at"))
    ).first()
    match = session.exec(
        select(TmdbMatch).where(TmdbMatch.media_item_id == item_id, TmdbMatch.selected)
    ).first()
    if not parsed or not match:
        raise HTTPException(status_code=400, detail="请先完成解析并选择 TMDB 匹配")
    plan = RenamePlannerService(session).build_plan(item, parsed, match, payload.operation)
    item.status = MediaStatus.PLANNED
    session.add(plan)
    session.add(item)
    session.commit()
    session.refresh(plan)
    return plan


@router.post("/rename-plans/{plan_id}/execute", response_model=RenamePlanRead)
def execute_rename_plan(plan_id: int, session: Session = Depends(get_session)) -> RenamePlan:
    plan = session.get(RenamePlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="重命名计划不存在")
    item = session.get(MediaItem, plan.media_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="资源不存在")
    if plan.status == "completed":
        return plan
    try:
        FileOperationService().execute(plan)
    except OSError as exc:
        plan.status = "failed"
        session.add(plan)
        session.commit()
        raise HTTPException(status_code=500, detail=f"文件操作失败：{exc}") from exc
    item.status = MediaStatus.COMPLETED
    session.add(plan)
    session.add(item)
    session.commit()
    session.refresh(plan)
    return plan


@router.get("/{item_id}/rename-plans", response_model=list[RenamePlanRead])
def list_rename_plans(item_id: int, session: Session = Depends(get_session)) -> list[RenamePlan]:
    return list(
        session.exec(
            select(RenamePlan)
            .where(RenamePlan.media_item_id == item_id)
            .order_by(desc("created_at"))
        ).all()
    )
