from logging.config import fileConfig
from core.configs import settings
from DB.database import Base
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
import asyncio
import os

from models import (User, UserSkill, Skill, EmailVerificationToken, PasswordResetToken, Service, ServiceRequest,
Job, JobApplication, Category, ConversationParticipant, Conversation, Message, Media, Notification, Report,
Review, TimeStampMixin, Business, PaymentProfile, FossaPayCustomer, PaymentIntent, Payout, WebhookEvent)
from alembic import context
from dotenv import load_dotenv

# 1. Grab the Alembic Config object FIRST
config = context.config


load_dotenv(override=True)

db_url = os.environ.get("DATABASE_URL")

if not db_url:
    raise ValueError("DATABASE_URL is missing! Make sure your .env file is in the right place.")

# 2. Print the URL so we can verify it in the terminal
print(f"🚀 Running migrations against: {db_url}")

config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))
