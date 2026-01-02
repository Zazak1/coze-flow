from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from storage.database.shared.model import CandidateEvaluation


class CandidateEvaluationCreate(BaseModel):
    """创建候选人评估的Pydantic模型"""
    resume_url: str = Field(..., description="简历文件URL")
    job_description: str = Field(..., description="岗位JD描述")
    final_score: float = Field(..., description="最终总分")
    candidate_level: str = Field(..., description="候选人等级")
    skill_score: float = Field(..., description="技能得分")
    project_score: float = Field(..., description="项目得分")
    stability_score: float = Field(..., description="稳定性得分")
    interview_questions: List[str] = Field(default=[], description="面试题列表")
    rejection_letter: str = Field(default="", description="拒信内容")


class CandidateEvaluationUpdate(BaseModel):
    """更新候选人评估的Pydantic模型"""
    final_score: Optional[float] = None
    candidate_level: Optional[str] = None
    interview_questions: Optional[List[str]] = None
    rejection_letter: Optional[str] = None


class CandidateEvaluationManager:
    """候选人评估数据管理器"""

    def create_evaluation(
        self,
        db: Session,
        evaluation_in: CandidateEvaluationCreate
    ) -> CandidateEvaluation:
        """
        创建新的候选人评估记录

        Args:
            db: 数据库会话
            evaluation_in: 创建数据

        Returns:
            创建的评估记录
        """
        evaluation_data = evaluation_in.model_dump()
        db_evaluation = CandidateEvaluation(**evaluation_data)
        db.add(db_evaluation)
        try:
            db.commit()
            db.refresh(db_evaluation)
            return db_evaluation
        except Exception:
            db.rollback()
            raise

    def get_evaluation_by_id(
        self,
        db: Session,
        evaluation_id: int
    ) -> Optional[CandidateEvaluation]:
        """
        根据ID获取评估记录

        Args:
            db: 数据库会话
            evaluation_id: 评估记录ID

        Returns:
            评估记录或None
        """
        return db.query(CandidateEvaluation).filter(
            CandidateEvaluation.id == evaluation_id
        ).first()

    def get_evaluations(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        candidate_level: Optional[str] = None,
        min_score: Optional[float] = None
    ) -> List[CandidateEvaluation]:
        """
        获取评估记录列表

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 返回记录数
            candidate_level: 筛选候选人等级
            min_score: 筛选最低分数

        Returns:
            评估记录列表
        """
        query = db.query(CandidateEvaluation)

        if candidate_level:
            query = query.filter(CandidateEvaluation.candidate_level == candidate_level)

        if min_score is not None:
            query = query.filter(CandidateEvaluation.final_score >= min_score)

        return query.order_by(CandidateEvaluation.created_at.desc()).offset(skip).limit(limit).all()

    def update_evaluation(
        self,
        db: Session,
        evaluation_id: int,
        evaluation_in: CandidateEvaluationUpdate
    ) -> Optional[CandidateEvaluation]:
        """
        更新评估记录

        Args:
            db: 数据库会话
            evaluation_id: 评估记录ID
            evaluation_in: 更新数据

        Returns:
            更新后的评估记录或None
        """
        db_evaluation = self.get_evaluation_by_id(db, evaluation_id)
        if not db_evaluation:
            return None

        update_data = evaluation_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_evaluation, field):
                setattr(db_evaluation, field, value)

        db.add(db_evaluation)
        try:
            db.commit()
            db.refresh(db_evaluation)
            return db_evaluation
        except Exception:
            db.rollback()
            raise

    def delete_evaluation(
        self,
        db: Session,
        evaluation_id: int
    ) -> bool:
        """
        删除评估记录

        Args:
            db: 数据库会话
            evaluation_id: 评估记录ID

        Returns:
            是否删除成功
        """
        db_evaluation = self.get_evaluation_by_id(db, evaluation_id)
        if not db_evaluation:
            return False

        try:
            db.delete(db_evaluation)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
