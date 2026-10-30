from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import (User, Conversation,ConversationParticipant, Message)
from schemas import ConversationResponse, MessageCreate, MessageResponse, ConversationListItem
from dependencies import get_current_user, get_db
from datetime import datetime, timezone
from sqlalchemy.orm import aliased


router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("/{user_id}", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Cannot start a conversation with yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot create a conversation with yourself.")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True, User.is_deleted == False))

    other_user = result.scalar_one_or_none()

    if not other_user:
        raise HTTPException(status_code=404,detail="User not found.")

    cp_me = aliased(ConversationParticipant)
    cp_other = aliased(ConversationParticipant)
    existing = (await db.execute(
        select(Conversation)
        .join(cp_me, cp_me.conversation_id == Conversation.id)
        .join(cp_other, cp_other.conversation_id == Conversation.id)
        .where(cp_me.user_id == current_user.id, cp_other.user_id == user_id)
    )).scalars().first()
    if existing:
        return existing
    # Create conversation
    conversation = Conversation()

    db.add(conversation)

    await db.flush()

    # Add current user
    participant1 = ConversationParticipant(
        conversation_id=conversation.id,
        user_id=current_user.id
    )

    # Add other user
    participant2 = ConversationParticipant(
        conversation_id=conversation.id,
        user_id=user_id
    )

    db.add_all([
        participant1,
        participant2
    ])

    await db.commit()
    await db.refresh(conversation)

    return conversation


@router.get("", response_model=list[ConversationListItem])
async def get_my_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    convs = (await db.execute(
        select(Conversation)
        .join(ConversationParticipant, Conversation.id == ConversationParticipant.conversation_id)
        .where(ConversationParticipant.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )).scalars().unique().all()
    if not convs:
        return []
    ids = [c.id for c in convs]

    others = {
        cid: user for cid, user in (await db.execute(
            select(ConversationParticipant.conversation_id, User)
            .join(User, User.id == ConversationParticipant.user_id)
            .where(
                ConversationParticipant.conversation_id.in_(ids),
                ConversationParticipant.user_id != current_user.id,
            )
        )).all()
    }

    unread = dict((await db.execute(
        select(Message.conversation_id, func.count())
        .where(
            Message.conversation_id.in_(ids),
            Message.sender_id != current_user.id,
            Message.is_read == False,
        )
        .group_by(Message.conversation_id)
    )).all())

    last = {
        m.conversation_id: m for m in (await db.execute(
            select(Message)
            .where(Message.conversation_id.in_(ids))
            .distinct(Message.conversation_id)
            .order_by(Message.conversation_id, Message.id.desc())
        )).scalars().all()
    }

    return [
        ConversationListItem(
            id=c.id,
            created_at=c.created_at,
            updated_at=c.updated_at,
            other_user=others.get(c.id),
            last_message=last.get(c.id),
            unread_count=unread.get(c.id, 0),
        )
        for c in convs
    ]


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(conversation_id: int, message_data: MessageCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):

    result = await db.execute(select(ConversationParticipant).where(ConversationParticipant.conversation_id == conversation_id, ConversationParticipant.user_id == current_user.id))

    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=403, detail="You are not a participant in this conversation.")

    # Create the message
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=message_data.content,
        is_read=False)

    db.add(message)

    conversation_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )

    conversation = conversation_result.scalar_one()

    conversation.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(message)

    return message


@router.get("/{conversation_id}/messages",response_model=list[MessageResponse])
async def get_messages(conversation_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), after_id: int | None = None):

    result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id))

    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=403, detail="You are not a participant in this conversation.")

    # Get messages
    query = select(Message).where(Message.conversation_id == conversation_id)
    if after_id is not None:
        query = query.where(Message.id > after_id)
    result = await db.execute(query.order_by(Message.created_at.asc()))
    messages = result.scalars().all()

    return messages


@router.patch("/{conversation_id}/messages/read")
async def mark_messages_as_read(conversation_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):

    # Make sure current user belongs to the conversation
    result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id))

    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(
            status_code=403,
            detail="You are not a participant in this conversation."
        )

    # Get unread messages sent by the other user
    result = await db.execute(
        select(Message).where(
            Message.conversation_id == conversation_id,
            Message.sender_id != current_user.id,
            Message.is_read == False
        )
    )

    messages = result.scalars().all()

    # Mark them as read
    for message in messages:
        message.is_read = True

    await db.commit()

    return {
        "message": "Messages marked as read.",
        "count": len(messages)
}
