from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, Integer, String, Text, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional
import datetime

class Base(DeclarativeBase):
    pass

class CandidateEvaluation(Base):
    """候选人评估结果表"""
    __tablename__ = "candidate_evaluations"

    id = Column(Integer, primary_key=True, comment="主键ID")
    resume_url = Column(String(1000), nullable=False, comment="简历文件URL")
    job_description = Column(Text, nullable=False, comment="岗位JD描述")
    final_score = Column(Float, nullable=False, comment="最终总分 (0-100)")
    candidate_level = Column(String(50), nullable=False, comment="候选人等级：高潜候选人/待定候选人/淘汰候选人")
    skill_score = Column(Float, nullable=False, comment="技能匹配度得分")
    project_score = Column(Float, nullable=False, comment="项目含金量得分")
    stability_score = Column(Float, nullable=False, comment="稳定性得分")
    interview_questions = Column(JSON, nullable=True, comment="面试题列表（JSON数组）")
    rejection_letter = Column(Text, nullable=True, comment="拒信内容")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="更新时间")

