from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import (User, Conversation,ConversationParticipant, Message)
from schemas import ConversationResponse, MessageCreate, MessageResponse
from dependencies import get_current_user, get_db
from datetime import datetime, timezone


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

    # Check if conversation already exists
    result = await db.execute(
        select(Conversation)
        .join(
            ConversationParticipant,
            Conversation.id == ConversationParticipant.conversation_id
        )
        .where(
            ConversationParticipant.user_id == current_user.id
        )
    )

    conversations = result.scalars().unique().all()

    for conversation in conversations:

        result = await db.execute(
            select(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id == conversation.id,
                ConversationParticipant.user_id == user_id
            )
        )

        participant = result.scalar_one_or_none()

        if participant:
            return conversation
            
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


@router.get("/", response_model=list[ConversationResponse])
async def get_my_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Conversation)
        .join(
            ConversationParticipant,
            Conversation.id == ConversationParticipant.conversation_id
        )
        .where(
            ConversationParticipant.user_id == current_user.id
        )
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().unique().all()

    return conversations 


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
async def get_messages(conversation_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):

    result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id))

    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=403, detail="You are not a participant in this conversation.")

    # Get messages
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )

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