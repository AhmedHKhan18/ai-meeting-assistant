"""Pydantic request/response models for the web API layer
(specs/002-web-frontend/contracts/api-endpoints.md).
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

# -- Auth --------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str


# -- Integrations --------------------------------------------------------


class IntegrationStatus(BaseModel):
    status: str
    masked_hint: str | None = None
    last_validated_at: str | None = None


class IntegrationsResponse(BaseModel):
    discord: IntegrationStatus
    trello: IntegrationStatus
    gemini: IntegrationStatus
    otter: IntegrationStatus


class DiscordCredentialRequest(BaseModel):
    bot_token: str = Field(min_length=1)


class TrelloCredentialRequest(BaseModel):
    api_key: str = Field(min_length=1)
    token: str = Field(min_length=1)
    board_id: str = Field(min_length=1)
    list_id: str = Field(min_length=1)


class GeminiCredentialRequest(BaseModel):
    api_key: str = Field(min_length=1)


# -- Dashboard -------------------------------------------------------------


class MeetingListItem(BaseModel):
    id: str
    title: str
    date: str
    duration_minutes: int | None
    processing_status: str


class MeetingListResponse(BaseModel):
    items: list[MeetingListItem]
    next_cursor: str | None = None


class Statement(BaseModel):
    text: str
    confident: bool


class MeetingSummaryResponse(BaseModel):
    overview: str
    discussion_points: list[str]
    decisions: list[Statement]
    risks: list[Statement]
    open_questions: list[str]
    follow_ups: list[Statement]


class TrackedTaskResponse(BaseModel):
    trello_card_id: str | None
    assignee: str | None
    due_date: str | None


class ActionItemResponse(BaseModel):
    id: str
    task_description: str
    owner: str | None
    deadline: str | None
    priority: str
    confidence: float
    tracked_task: TrackedTaskResponse | None = None


class MeetingDetailResponse(BaseModel):
    id: str
    title: str
    date: str
    duration_minutes: int | None
    processing_status: str
    summary: MeetingSummaryResponse | None
    action_items: list[ActionItemResponse]


class TaskListResponse(BaseModel):
    items: list[ActionItemResponse]


class ReportItem(BaseModel):
    id: str
    report_type: str
    report_date: str
    content: dict
    delivery_status: str


class ReportListResponse(BaseModel):
    items: list[ReportItem]


# -- Assistant --------------------------------------------------------------


class AssistantStatusResponse(BaseModel):
    status: str
    last_activity_at: str | None
    last_error: str | None
    missing_integrations: list[str] = Field(default_factory=list)
