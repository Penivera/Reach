from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey
from DB.database import Base
from .mixins import TimeStampMixin

class Skill(Base, TimeStampMixin):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
    )

    user_skills = relationship("UserSkill", 
                               back_populates="skill")



class UserSkill(Base, TimeStampMixin):
    __tablename__ = "user_skills"


    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        primary_key=True
    )

    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id"),
        primary_key=True
    )

    user = relationship(
    "User",
    back_populates="user_skills"
)

    skill = relationship(
    "Skill",
    back_populates="user_skills")