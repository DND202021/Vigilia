"""Communication Hub API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.communication_hub import (
    CommunicationHub,
    MessageChannel,
    MessagePriority,
)

router = APIRouter()


class TemplateResponse(BaseModel):
    """Message template response."""

    id: str
    name: str
    subject: str
    body: str
    channels: list[str]
    variables: list[str]


class SendMessageRequest(BaseModel):
    """Request to send a custom message."""

    subject: str
    body: str
    channels: list[MessageChannel]
    priority: MessagePriority = MessagePriority.NORMAL
    recipients: list[str] | None = None


class RenderedMessageResponse(BaseModel):
    """Rendered message response."""

    subject: str
    body: str
    channel: str
    priority: str


class RenderTemplateRequest(BaseModel):
    """Request to render a template."""

    template_id: str
    variables: dict
    channel: MessageChannel | None = None
    priority: MessagePriority = MessagePriority.NORMAL


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TemplateResponse]:
    """List all available message templates."""
    hub = CommunicationHub(db)
    templates = hub.list_templates()

    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            subject=t.subject,
            body=t.body,
            channels=[c.value for c in t.channels],
            variables=t.variables,
        )
        for t in templates
    ]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TemplateResponse:
    """Get a specific message template."""
    hub = CommunicationHub(db)
    template = hub.get_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return TemplateResponse(
        id=template.id,
        name=template.name,
        subject=template.subject,
        body=template.body,
        channels=[c.value for c in template.channels],
        variables=template.variables,
    )


@router.post("/render", response_model=RenderedMessageResponse)
async def render_template(
    request: RenderTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RenderedMessageResponse:
    """Render a template with variables (preview)."""
    hub = CommunicationHub(db)

    message = hub.render_template(
        template_id=request.template_id,
        variables=request.variables,
        channel=request.channel,
        priority=request.priority,
    )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return RenderedMessageResponse(
        subject=message.subject,
        body=message.body,
        channel=message.channel.value,
        priority=message.priority.value,
    )


@router.post("/send", response_model=list[RenderedMessageResponse])
async def send_message(
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[RenderedMessageResponse]:
    """Send a custom message to specified channels.

    Note: This endpoint prepares messages but actual delivery
    depends on configured notification providers.
    """
    hub = CommunicationHub(db)

    messages = await hub.send_custom_message(
        subject=request.subject,
        body=request.body,
        channels=request.channels,
        priority=request.priority,
        recipients=request.recipients,
    )

    # In a real implementation, messages would be queued for delivery here

    return [
        RenderedMessageResponse(
            subject=m.subject,
            body=m.body,
            channel=m.channel.value,
            priority=m.priority.value,
        )
        for m in messages
    ]
