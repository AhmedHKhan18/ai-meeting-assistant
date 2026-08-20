"""Dashboard read endpoints (User Story 3): meetings, tasks, reports — all
scoped to the signed-in user's own data (FR-013, contracts/api-endpoints.md
Dashboard section). Read-only in this feature (Out of Scope: editing via UI).
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_current_user, get_db
from api.schemas import (
    ActionItemResponse,
    MeetingDetailResponse,
    MeetingListItem,
    MeetingListResponse,
    MeetingSummaryResponse,
    ReportItem,
    ReportListResponse,
    TaskListResponse,
    TrackedTaskResponse,
)
from models.action_item import get_action_items_for_meeting, get_action_items_for_user
from models.daily_report import get_reports_for_user
from models.meeting import Meeting, get_meeting, get_meetings_for_user
from models.summary import get_summary_by_meeting
from models.tracked_task import get_tracked_task_by_action_item
from models.user import User

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


def _to_list_item(meeting: Meeting) -> MeetingListItem:
    return MeetingListItem(
        id=meeting.id,
        title=meeting.title,
        date=meeting.date,
        duration_minutes=meeting.duration_minutes,
        processing_status=meeting.processing_status,
    )


def _to_action_item_response(conn: sqlite3.Connection, item) -> ActionItemResponse:
    tracked = get_tracked_task_by_action_item(conn, item.id)
    return ActionItemResponse(
        id=item.id,
        task_description=item.task_description,
        owner=item.owner,
        deadline=item.deadline,
        priority=item.priority,
        confidence=item.confidence,
        tracked_task=(
            TrackedTaskResponse(
                trello_card_id=tracked.trello_card_id, assignee=tracked.assignee, due_date=tracked.due_date
            )
            if tracked
            else None
        ),
    )


@router.get("/meetings", response_model=MeetingListResponse)
async def list_meetings(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> MeetingListResponse:
    meetings = get_meetings_for_user(conn, user.id, limit=limit, before=cursor)
    next_cursor = meetings[-1].updated_at if len(meetings) == limit else None
    return MeetingListResponse(items=[_to_list_item(m) for m in meetings], next_cursor=next_cursor)


@router.get("/meetings/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting_detail(
    meeting_id: str,
    user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> MeetingDetailResponse:
    meeting = get_meeting(conn, user.id, meeting_id)
    if meeting is None:
        # Identical response whether it doesn't exist or belongs to another
        # user (contracts/api-endpoints.md) — never confirm another user's data exists.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="meeting not found")

    summary = get_summary_by_meeting(conn, meeting.id)
    action_items = get_action_items_for_meeting(conn, meeting.id)

    return MeetingDetailResponse(
        id=meeting.id,
        title=meeting.title,
        date=meeting.date,
        duration_minutes=meeting.duration_minutes,
        processing_status=meeting.processing_status,
        summary=(
            # models/summary.py stores decisions/risks/follow_ups as raw
            # list[dict] (JSON-decoded straight from meeting_summaries) —
            # Pydantic validates each dict into a Statement at construction
            # time, so this is a safe runtime coercion mypy can't see statically.
            MeetingSummaryResponse(
                overview=summary.overview,
                discussion_points=summary.discussion_points,
                decisions=summary.decisions,  # type: ignore[arg-type]
                risks=summary.risks,  # type: ignore[arg-type]
                open_questions=summary.open_questions,
                follow_ups=summary.follow_ups,  # type: ignore[arg-type]
            )
            if summary
            else None
        ),
        action_items=[_to_action_item_response(conn, item) for item in action_items],
    )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status_filter: str = Query("outstanding", alias="status"),
    user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> TaskListResponse:
    # "outstanding" and "all" currently return the same set — this API layer
    # doesn't do a live Trello completion sync (feature 001's own Discord
    # /tasks command doesn't either by default), so every tracked action item
    # is treated as outstanding until a future feature adds real completion
    # tracking. Both values are accepted so the frontend/contract can adopt
    # real filtering later without a breaking API change.
    del status_filter
    items = get_action_items_for_user(conn, user.id)
    return TaskListResponse(items=[_to_action_item_response(conn, item) for item in items])


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    report_type: str | None = Query(None, alias="type"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> ReportListResponse:
    if report_type and report_type not in ("morning", "evening"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type must be morning or evening")

    reports = get_reports_for_user(conn, user.id, report_type=report_type, limit=limit)
    return ReportListResponse(
        items=[
            ReportItem(
                id=r.id,
                report_type=r.report_type,
                report_date=r.report_date,
                content=r.content,
                delivery_status=r.delivery_status,
            )
            for r in reports
        ]
    )
