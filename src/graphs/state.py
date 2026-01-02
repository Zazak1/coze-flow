from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from utils.file.file import File

# ==================== 全局状态定义 ====================
class GlobalState(BaseModel):
    """工作流全局状态定义"""
    # 输入数据
    resume_url: str = Field(..., description="简历文件的链接")
    job_description: str = Field(..., description="岗位JD描述")

    # 岗位分类
    job_category: str = Field(default="未知", description="岗位类别：python_engineer/frontend_engineer/other")

    # 数据处理阶段
    resume_text: str = Field(default="", description="解析后的简历文本")
    anonymized_text: str = Field(default="", description="脱敏后的文本")

    # 结构化数据
    structured_data: Dict[str, Any] = Field(default={}, description="结构化数据JSON")
    candidate_skills: List[str] = Field(default=[], description="候选人技能列表")
    years_of_experience: int = Field(default=0, description="工作年限")
    project_list: List[Dict[str, Any]] = Field(default=[], description="项目列表")
    previous_companies: List[str] = Field(default=[], description="历史公司列表")

    # JD解析
    min_years_required: int = Field(default=0, description="JD要求的最低工作年限")

    # 初筛结果
    passes_initial_filter: bool = Field(default=False, description="是否通过初筛")

    # 评估得分
    skill_score: float = Field(default=0.0, description="技能匹配度得分 (0-100)")
    project_score: float = Field(default=0.0, description="项目含金量得分 (0-100)")
    stability_score: float = Field(default=0.0, description="稳定性得分 (0-100)")
    background_check_results: List[Dict[str, Any]] = Field(default=[], description="背景调查结果")

    # 最终结果
    final_score: float = Field(default=0.0, description="最终加权总分 (0-100)")
    candidate_level: str = Field(default="", description="候选人等级：高潜候选人/待定候选人/淘汰候选人")
    interview_questions: List[str] = Field(default=[], description="面试题列表")
    rejection_letter: str = Field(default="", description="拒信内容")

    # 数据库存储
    candidate_record_id: Optional[int] = Field(default=None, description="候选人记录ID")


# ==================== 图的输入输出定义 ====================
class GraphInput(BaseModel):
    """工作流输入"""
    resume_url: str = Field(..., description="简历文件的链接（支持http/https URL）")
    job_description: str = Field(..., description="岗位JD描述")


class GraphOutput(BaseModel):
    """工作流输出"""
    final_report: Dict[str, Any] = Field(..., description="最终报告JSON，包含总分、评级、面试题或拒信")


# ==================== 节点输入输出定义 ====================

# --- 岗位分类节点 ---
class JobCategoryInput(BaseModel):
    """岗位分类节点输入"""
    job_description: str = Field(..., description="岗位JD描述")


class JobCategoryOutput(BaseModel):
    """岗位分类节点输出"""
    job_category: str = Field(..., description="岗位类别：python_engineer/frontend_engineer/other")


# --- 文档解析节点 ---
class DocumentParseInput(BaseModel):
    """文档解析节点输入"""
    resume_url: str = Field(..., description="简历文件的链接")


class DocumentParseOutput(BaseModel):
    """文档解析节点输出"""
    resume_text: str = Field(..., description="解析后的简历文本")


# --- 隐私脱敏节点 ---
class PrivacyAnonymizeInput(BaseModel):
    """隐私脱敏节点输入"""
    resume_text: str = Field(..., description="原始简历文本")


class PrivacyAnonymizeOutput(BaseModel):
    """隐私脱敏节点输出"""
    anonymized_text: str = Field(..., description="脱敏后的简历文本")


# --- 结构化提取节点 ---
class StructuredExtractInput(BaseModel):
    """结构化提取节点输入"""
    anonymized_text: str = Field(..., description="脱敏后的简历文本")


class StructuredExtractOutput(BaseModel):
    """结构化提取节点输出"""
    candidate_skills: List[str] = Field(..., description="候选人技能列表")
    years_of_experience: int = Field(..., description="工作年限")
    project_list: List[Dict[str, Any]] = Field(..., description="项目列表")
    previous_companies: List[str] = Field(..., description="历史公司列表")


# --- 初筛逻辑节点 ---
class InitialFilterInput(BaseModel):
    """初筛逻辑节点输入"""
    years_of_experience: int = Field(..., description="工作年限")
    job_description: str = Field(..., description="岗位JD描述")


class InitialFilterOutput(BaseModel):
    """初筛逻辑节点输出"""
    passes_initial_filter: bool = Field(..., description="是否通过初筛")
    min_years_required: int = Field(..., description="JD要求的最低工作年限")


# --- 技能匹配度打分节点 ---
class SkillMatchInput(BaseModel):
    """技能匹配度打分节点输入"""
    job_description: str = Field(..., description="岗位JD描述")
    candidate_skills: List[str] = Field(..., description="候选人技能列表")


class SkillMatchOutput(BaseModel):
    """技能匹配度打分节点输出"""
    skill_score: float = Field(..., description="技能匹配度得分 (0-100)")
    skill_reason: str = Field(..., description="打分理由")


# --- 项目含金量评估节点 ---
class ProjectQualityInput(BaseModel):
    """项目含金量评估节点输入"""
    project_list: List[Dict[str, Any]] = Field(..., description="项目列表")


class ProjectQualityOutput(BaseModel):
    """项目含金量评估节点输出"""
    project_score: float = Field(..., description="项目含金量得分 (0-100)")
    project_reason: str = Field(..., description="打分理由")


# --- 背景调查节点 ---
class BackgroundCheckInput(BaseModel):
    """背景调查节点输入"""
    previous_companies: List[str] = Field(..., description="历史公司列表")


class BackgroundCheckOutput(BaseModel):
    """背景调查节点输出"""
    background_check_results: List[Dict[str, Any]] = Field(..., description="背景调查结果列表")


# --- 稳定性评估节点 ---
class StabilityAssessInput(BaseModel):
    """稳定性评估节点输入"""
    background_check_results: List[Dict[str, Any]] = Field(..., description="背景调查结果")
    previous_companies: List[str] = Field(..., description="历史公司列表")


class StabilityAssessOutput(BaseModel):
    """稳定性评估节点输出"""
    stability_score: float = Field(..., description="稳定性得分 (0-100)")
    stability_reason: str = Field(..., description="评估理由")


# --- 加权计算节点 ---
class WeightedScoreInput(BaseModel):
    """加权计算节点输入"""
    skill_score: float = Field(..., description="技能匹配度得分 (0-100)")
    project_score: float = Field(..., description="项目含金量得分 (0-100)")
    stability_score: float = Field(..., description="稳定性得分 (0-100)")


class WeightedScoreOutput(BaseModel):
    """加权计算节点输出"""
    final_score: float = Field(..., description="最终加权总分 (0-100)")
    candidate_level: str = Field(..., description="候选人等级")


# --- 定制面试题/拒信节点 ---
class GenerateContentInput(BaseModel):
    """定制面试题/拒信节点输入"""
    candidate_level: str = Field(..., description="候选人等级")
    skill_reason: str = Field(..., description="技能评估理由")
    project_reason: str = Field(..., description="项目评估理由")
    stability_reason: str = Field(..., description="稳定性评估理由")
    candidate_skills: List[str] = Field(..., description="候选人技能列表")


class GenerateContentOutput(BaseModel):
    """定制面试题/拒信节点输出"""
    interview_questions: List[str] = Field(default=[], description="面试题列表（高潜/待定候选人）")
    rejection_letter: str = Field(default="", description="拒信内容（淘汰候选人）")


# --- 数据存档节点 ---
class SaveToDatabaseInput(BaseModel):
    """数据存档节点输入"""
    resume_url: str = Field(..., description="简历文件链接")
    job_description: str = Field(..., description="岗位JD描述")
    final_score: float = Field(..., description="最终得分")
    candidate_level: str = Field(..., description="候选人等级")
    skill_score: float = Field(..., description="技能得分")
    project_score: float = Field(..., description="项目得分")
    stability_score: float = Field(..., description="稳定性得分")
    interview_questions: List[str] = Field(default=[], description="面试题")
    rejection_letter: str = Field(default="", description="拒信")


class SaveToDatabaseOutput(BaseModel):
    """数据存档节点输出"""
    candidate_record_id: int = Field(..., description="候选人记录ID")


# --- 最终报告生成节点 ---
class GenerateReportInput(BaseModel):
    """最终报告生成节点输入"""
    job_category: str = Field(default="未知", description="岗位类别")
    final_score: float = Field(default=0.0, description="最终得分")
    candidate_level: str = Field(default="未评估", description="候选人等级")
    interview_questions: List[str] = Field(default=[], description="面试题")
    rejection_letter: str = Field(default="", description="拒信")
    skill_score: float = Field(default=0.0, description="技能得分")
    project_score: float = Field(default=0.0, description="项目得分")
    stability_score: float = Field(default=0.0, description="稳定性得分")


class GenerateReportOutput(BaseModel):
    """最终报告生成节点输出"""
    final_report: Dict[str, Any] = Field(..., description="最终报告JSON")
