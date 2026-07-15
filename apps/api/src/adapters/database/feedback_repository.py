"""Feedback Database Repository.

Implements the FeedbackRepository port using SQLAlchemy ORM with RLS.
"""

from typing import Any
import uuid

from sqlalchemy import select, func

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import ChatMessageFeedbackDb
from src.domain.abstractions.inference import ChatMessageFeedback, FeedbackRepository


class SqlFeedbackRepository(FeedbackRepository):
    """SQLAlchemy-backed feedback repository."""

    async def submit_feedback(self, feedback: ChatMessageFeedback) -> None:
        """Submit or update feedback for a message."""
        tenant_id = feedback.tenant_id
        message_id = uuid.UUID(feedback.message_id)

        async with tenant_session(tenant_id=tenant_id) as session:
            # Check for existing feedback on this message
            stmt = select(ChatMessageFeedbackDb).where(
                ChatMessageFeedbackDb.tenant_id == uuid.UUID(tenant_id),
                ChatMessageFeedbackDb.message_id == message_id,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row:
                # Update existing
                row.rating = feedback.rating
                row.feedback_text = feedback.feedback_text
                if feedback.user_id:
                    row.user_id = uuid.UUID(feedback.user_id)
            else:
                # Create new
                feedback_id = uuid.UUID(feedback.feedback_id) if feedback.feedback_id else uuid.uuid4()
                user_id = uuid.UUID(feedback.user_id) if feedback.user_id else None
                row = ChatMessageFeedbackDb(
                    feedback_id=feedback_id,
                    tenant_id=uuid.UUID(tenant_id),
                    message_id=message_id,
                    user_id=user_id,
                    rating=feedback.rating,
                    feedback_text=feedback.feedback_text,
                )
                session.add(row)

            await session.commit()

    async def get_feedback_analytics(self, tenant_id: str) -> dict[str, Any]:
        """Aggregate thumbs up/down count ratios and recent comments."""
        async with tenant_session(tenant_id=tenant_id) as session:
            # Thumbs up (+1) count query
            stmt_up = select(func.count(ChatMessageFeedbackDb.feedback_id)).where(
                ChatMessageFeedbackDb.tenant_id == uuid.UUID(tenant_id),
                ChatMessageFeedbackDb.rating > 0,
            )
            res_up = await session.execute(stmt_up)
            up_count = res_up.scalar() or 0

            # Thumbs down (< 0) count query
            stmt_down = select(func.count(ChatMessageFeedbackDb.feedback_id)).where(
                ChatMessageFeedbackDb.tenant_id == uuid.UUID(tenant_id),
                ChatMessageFeedbackDb.rating <= 0,
            )
            res_down = await session.execute(stmt_down)
            down_count = res_down.scalar() or 0

            # Recent comments query
            stmt_comments = (
                select(ChatMessageFeedbackDb)
                .where(
                    ChatMessageFeedbackDb.tenant_id == uuid.UUID(tenant_id),
                    ChatMessageFeedbackDb.feedback_text.isnot(None),
                    ChatMessageFeedbackDb.feedback_text != "",
                )
                .order_by(ChatMessageFeedbackDb.created_at.desc())
                .limit(10)
            )
            res_comments = await session.execute(stmt_comments)
            comments_rows = res_comments.scalars().all()

            comments_list = [
                {
                    "feedback_id": str(c.feedback_id),
                    "message_id": str(c.message_id),
                    "user_id": str(c.user_id) if c.user_id else None,
                    "rating": c.rating,
                    "text": c.feedback_text,
                    "created_at": c.created_at.isoformat(),
                }
                for c in comments_rows
            ]

            total = up_count + down_count
            percentage_positive = (up_count / total * 100) if total > 0 else 100.0

            return {
                "tenant_id": tenant_id,
                "total_feedback_count": total,
                "positive_count": up_count,
                "negative_count": down_count,
                "positive_percentage": round(percentage_positive, 2),
                "recent_comments": comments_list,
            }
