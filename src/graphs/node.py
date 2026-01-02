import os
import json
import re
from typing import Iterator
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessageChunk
from langchain_openai import ChatOpenAI
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context, default_headers
from jinja2 import Template
from cozeloop.decorator import observe

from graphs.state import (
    # 岗位分类
    JobCategoryInput, JobCategoryOutput,
    # 文档解析
    DocumentParseInput, DocumentParseOutput,
    # 隐私脱敏
    PrivacyAnonymizeInput, PrivacyAnonymizeOutput,
    # 结构化提取
    StructuredExtractInput, StructuredExtractOutput,
    # 初筛逻辑
    InitialFilterInput, InitialFilterOutput,
    # 技能匹配
    SkillMatchInput, SkillMatchOutput,
    # 项目评估
    ProjectQualityInput, ProjectQualityOutput,
    # 背景调查
    BackgroundCheckInput, BackgroundCheckOutput,
    # 稳定性评估
    StabilityAssessInput, StabilityAssessOutput,
    # 加权计算
    WeightedScoreInput, WeightedScoreOutput,
    # 生成内容
    GenerateContentInput, GenerateContentOutput,
    # 数据存档
    SaveToDatabaseInput, SaveToDatabaseOutput,
    # 最终报告
    GenerateReportInput, GenerateReportOutput,
)

from utils.file.file import File, FileOps


# ==================== 通用函数 ====================

def call_llm(ctx: Context, messages: list, config: dict) -> Iterator[BaseMessageChunk]:
    """
    调用大语言模型的通用函数

    Args:
        ctx: 上下文对象
        messages: 消息列表
        config: 模型配置
    """
    api_key: str = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url: str = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    llm = ChatOpenAI(
        model=config.get("model", "doubao-seed-1-6-251015"),
        api_key=api_key,
        base_url=base_url,
        streaming=True,
        extra_body={
            "thinking": {
                "type": config.get("thinking", "disabled"),
            }
        },
        temperature=config.get("temperature", 0.7),
        frequency_penalty=config.get("frequency_penalty", 0),
        top_p=config.get("top_p", 0.7),
        max_tokens=config.get("max_tokens", 4096),
        default_headers=default_headers(ctx),
    )

    for chunk in llm.stream(messages):
        # 确保 chunk.content 是字符串类型
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        yield chunk


def read_llm_config(config_file_path: str) -> dict:
    """
    读取大语言模型配置文件

    Args:
        config_file_path: 配置文件相对路径

    Returns:
        配置字典
    """
    full_path = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config_file_path)
    with open(full_path, 'r', encoding='utf-8') as fd:
        return json.load(fd)


# ==================== 节点函数实现 ====================

# --- 0. 岗位分类节点 ---
def job_category_node(state: JobCategoryInput, config: RunnableConfig, runtime: Runtime[Context]) -> JobCategoryOutput:
    """
    title: 岗位分类
    desc: 根据JD描述识别岗位类别：python_engineer/frontend_engineer/other
    integrations: 大语言模型
    """
    ctx = runtime.context

    # 读取配置文件
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)

    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")

    # 渲染 user prompt
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({"job_description": state.job_description})

    # 组装消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]

    # 调用 LLM
    full_response = ""
    for chunk in call_llm(ctx, messages, llm_config):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        full_response += content

    # 解析结果
    try:
        # 尝试提取 JSON 部分
        json_match = re.search(r'\{[\s\S]*\}', full_response)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(full_response)

        job_category = result.get("job_category", "other")

        # 验证类别是否合法
        valid_categories = ["python_engineer", "frontend_engineer", "other"]
        if job_category not in valid_categories:
            job_category = "other"

        return JobCategoryOutput(job_category=job_category)
    except Exception as e:
        # 如果解析失败，默认返回 other
        return JobCategoryOutput(job_category="other")


# --- 1. 文档解析节点 ---
def document_parse_node(state: DocumentParseInput, config: RunnableConfig, runtime: Runtime[Context]) -> DocumentParseOutput:
    """
    title: 文档解析
    desc: 解析简历文件URL，提取文本内容
    integrations:
    """
    ctx = runtime.context

    try:
        # 创建 File 对象
        file_obj = File(url=state.resume_url)

        # 提取文本内容
        resume_text = FileOps.extract_text(file_obj)

        return DocumentParseOutput(resume_text=resume_text)

    except Exception as e:
        raise Exception(f"文档解析失败: {str(e)}")


# --- 2. 隐私脱敏节点 ---
def privacy_anonymize_node(state: PrivacyAnonymizeInput, config: RunnableConfig, runtime: Runtime[Context]) -> PrivacyAnonymizeOutput:
    """
    title: 隐私脱敏
    desc: 对简历文本进行隐私脱敏，将姓名、手机号、邮箱等信息替换为 [HIDDEN]
    integrations: 大语言模型
    """
    ctx = runtime.context

    # 读取配置文件
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)

    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")

    # 渲染 user prompt
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({"resume_text": state.resume_text})

    # 组装消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]

    # 调用 LLM
    full_response = ""
    for chunk in call_llm(ctx, messages, llm_config):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        full_response += content

    return PrivacyAnonymizeOutput(anonymized_text=full_response.strip())


# --- 3. 结构化提取节点 ---
def structured_extract_node(state: StructuredExtractInput, config: RunnableConfig, runtime: Runtime[Context]) -> StructuredExtractOutput:
    """
    title: 结构化提取
    desc: 将脱敏后的简历文本转换为结构化JSON格式，提取技能、工作年限、项目、历史公司等信息
    integrations: 大语言模型
    """
    ctx = runtime.context

    # 读取配置文件
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)

    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")

    # 渲染 user prompt
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({"anonymized_text": state.anonymized_text})

    # 组装消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]

    # 调用 LLM
    full_response = ""
    for chunk in call_llm(ctx, messages, llm_config):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        full_response += content

    # 解析 JSON
    try:
        # 尝试提取 JSON 部分
        json_match = re.search(r'\{[\s\S]*\}', full_response)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(full_response)

        candidate_skills = result.get("candidate_skills", [])
        years_of_experience = result.get("years_of_experience", 0)
        project_list = result.get("project_list", [])
        previous_companies = result.get("previous_companies", [])

        return StructuredExtractOutput(
            candidate_skills=candidate_skills,
            years_of_experience=int(years_of_experience),
            project_list=project_list,
            previous_companies=previous_companies
        )
    except Exception as e:
        # 如果解析失败，返回默认值
        return StructuredExtractOutput(
            candidate_skills=[],
            years_of_experience=0,
            project_list=[],
            previous_companies=[]
        )


# --- 4. 初筛逻辑节点 ---
def initial_filter_node(state: InitialFilterInput, config: RunnableConfig, runtime: Runtime[Context]) -> InitialFilterOutput:
    """
    title: 初筛逻辑
    desc: 判断候选人工作年限是否满足JD的最低要求
    integrations:
    """
    ctx = runtime.context

    # 从 JD 中提取最低年限要求
    # 简单的正则匹配，例如："3年以上"、"至少2年"、"3-5年"等
    job_desc = state.job_description.lower()

    # 尝试匹配年限要求
    patterns = [
        r'(\d+)\s*年\s*以上',
        r'至少\s*(\d+)\s*年',
        r'(\d+)\s*-\s*(\d+)\s*年',
        r'(\d+)\s*\+\s*年',
    ]

    min_years = 0
    for pattern in patterns:
        match = re.search(pattern, job_desc)
        if match:
            if '-' in pattern:
                # 范围取最小值
                min_years = int(match.group(1))
            else:
                min_years = int(match.group(1))
            break

    # 判断是否满足要求
    passes_filter = state.years_of_experience >= min_years

    return InitialFilterOutput(
        passes_initial_filter=passes_filter,
        min_years_required=min_years
    )


# --- 5. 技能匹配度打分节点 ---
def skill_match_node(state: SkillMatchInput, config: RunnableConfig, runtime: Runtime[Context]) -> SkillMatchOutput:
    """
    title: 技能匹配度打分
    desc: 对比岗位JD和候选人技能，给出匹配度得分 (0-100) 和详细理由
    integrations: 大语言模型
    """
    ctx = runtime.context

    # 读取配置文件
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)

    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")

    # 渲染 user prompt
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({
        "job_description": state.job_description,
        "candidate_skills": json.dumps(state.candidate_skills, ensure_ascii=False)
    })

    # 组装消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]

    # 调用 LLM
    full_response = ""
    for chunk in call_llm(ctx, messages, llm_config):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        full_response += content

    # 解析结果
    try:
        json_match = re.search(r'\{[\s\S]*\}', full_response)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(full_response)

        skill_score = float(result.get("score", 50))
        skill_reason = result.get("reason", full_response)

        return SkillMatchOutput(
            skill_score=skill_score,
            skill_reason=skill_reason
        )
    except Exception as e:
        return SkillMatchOutput(skill_score=50.0, skill_reason=full_response)


# --- 6. 项目含金量评估节点 ---
def project_quality_node(state: ProjectQualityInput, config: RunnableConfig, runtime: Runtime[Context]) -> ProjectQualityOutput:
    """
    title: 项目含金量评估
    desc: 基于STAR法则评估项目难度和贡献度，打分 (0-100)
    integrations: 大语言模型
    """
    ctx = runtime.context

    # 读取配置文件
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)

    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")

    # 渲染 user prompt
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({
        "project_list": json.dumps(state.project_list, ensure_ascii=False)
    })

    # 组装消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]

    # 调用 LLM
    full_response = ""
    for chunk in call_llm(ctx, messages, llm_config):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        full_response += content

    # 解析结果
    try:
        json_match = re.search(r'\{[\s\S]*\}', full_response)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(full_response)

        project_score = float(result.get("score", 50))
        project_reason = result.get("reason", full_response)

        return ProjectQualityOutput(
            project_score=project_score,
            project_reason=project_reason
        )
    except Exception as e:
        return ProjectQualityOutput(project_score=50.0, project_reason=full_response)


# --- 7. 背景调查节点 ---
@observe
def background_check_node(state: BackgroundCheckInput, config: RunnableConfig, runtime: Runtime[Context]) -> BackgroundCheckOutput:
    """
    title: 背景调查
    desc: 使用搜索引擎验证候选人历史公司的真实性
    integrations: 联网搜索
    """
    ctx = runtime.context

    results = []

    # 为每家公司进行搜索
    for company in state.previous_companies:
        try:
            # 导入搜索函数
            import requests
            api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
            base_url = os.getenv("COZE_INTEGRATION_BASE_URL")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            headers.update(default_headers(ctx))

            request = {
                "Query": company,
                "SearchType": "web",
                "Count": 3,
                "NeedSummary": True,
            }

            response = requests.post(f'{base_url}/api/search_api/web_search', json=request, headers=headers)
            response.raise_for_status()

            data = response.json()
            result = data.get("Result", {})

            if result.get("WebResults"):
                web_items = result.get("WebResults", [])[:3]
                for item in web_items:
                    results.append({
                        "company": company,
                        "title": item.get("Title", ""),
                        "url": item.get("Url", ""),
                        "snippet": item.get("Snippet", ""),
                        "auth_level": item.get("AuthInfoLevel", 0)
                    })

        except Exception as e:
            # 记录错误但继续处理其他公司
            results.append({
                "company": company,
                "error": str(e),
                "auth_level": 0
            })

    return BackgroundCheckOutput(background_check_results=results)


# --- 8. 稳定性评估节点 ---
def stability_assess_node(state: StabilityAssessInput, config: RunnableConfig, runtime: Runtime[Context]) -> StabilityAssessOutput:
    """
    title: 稳定性评估
    desc: 结合背景调查结果和跳槽频率，评估候选人稳定性
    integrations: 大语言模型
    """
    ctx = runtime.context

    # 读取配置文件
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)

    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")

    # 渲染 user prompt
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({
        "background_check_results": json.dumps(state.background_check_results, ensure_ascii=False),
        "previous_companies": json.dumps(state.previous_companies, ensure_ascii=False)
    })

    # 组装消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]

    # 调用 LLM
    full_response = ""
    for chunk in call_llm(ctx, messages, llm_config):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        full_response += content

    # 解析结果
    try:
        json_match = re.search(r'\{[\s\S]*\}', full_response)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(full_response)

        stability_score = float(result.get("score", 50))
        stability_reason = result.get("reason", full_response)

        return StabilityAssessOutput(
            stability_score=stability_score,
            stability_reason=stability_reason
        )
    except Exception as e:
        return StabilityAssessOutput(stability_score=50.0, stability_reason=full_response)


# --- 9. 加权计算节点 ---
def weighted_score_node(state: WeightedScoreInput, config: RunnableConfig, runtime: Runtime[Context]) -> WeightedScoreOutput:
    """
    title: 加权计算
    desc: 按权重计算最终总分（技能40% + 项目40% + 稳定性20%），并确定候选人等级
    integrations:
    """
    ctx = runtime.context

    # 计算加权总分
    final_score = (
        state.skill_score * 0.4 +
        state.project_score * 0.4 +
        state.stability_score * 0.2
    )

    # 四舍五入保留两位小数
    final_score = round(final_score, 2)

    # 确定候选人等级
    if final_score >= 80:
        candidate_level = "高潜候选人"
    elif final_score >= 60:
        candidate_level = "待定候选人"
    else:
        candidate_level = "淘汰候选人"

    return WeightedScoreOutput(
        final_score=final_score,
        candidate_level=candidate_level
    )


# --- 10. 定制面试题/拒信节点 ---
def generate_content_node(state: GenerateContentInput, config: RunnableConfig, runtime: Runtime[Context]) -> GenerateContentOutput:
    """
    title: 定制面试题/拒信
    desc: 根据候选人等级生成面试题（高潜/待定）或拒信（淘汰）
    integrations: 大语言模型
    """
    ctx = runtime.context

    # 读取配置文件
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)

    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")

    # 渲染 user prompt
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({
        "candidate_level": state.candidate_level,
        "skill_reason": state.skill_reason,
        "project_reason": state.project_reason,
        "stability_reason": state.stability_reason,
        "candidate_skills": json.dumps(state.candidate_skills, ensure_ascii=False)
    })

    # 组装消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]

    # 调用 LLM
    full_response = ""
    for chunk in call_llm(ctx, messages, llm_config):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        full_response += content

    # 解析结果
    if state.candidate_level == "淘汰候选人":
        # 淘汰候选人，返回拒信
        return GenerateContentOutput(
            interview_questions=[],
            rejection_letter=full_response.strip()
        )
    else:
        # 高潜或待定，返回面试题
        try:
            json_match = re.search(r'\{[\s\S]*\}', full_response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(full_response)

            interview_questions = result.get("interview_questions", [])
            return GenerateContentOutput(
                interview_questions=interview_questions,
                rejection_letter=""
            )
        except Exception as e:
            return GenerateContentOutput(
                interview_questions=[full_response],
                rejection_letter=""
            )


# --- 11. 数据存档节点 ---
def save_to_database_node(state: SaveToDatabaseInput, config: RunnableConfig, runtime: Runtime[Context]) -> SaveToDatabaseOutput:
    """
    title: 数据存档
    desc: 将候选人评估结果存入数据库
    integrations: 数据库
    """
    ctx = runtime.context

    try:
        from storage.database.db import get_session
        from storage.database.shared.model import CandidateEvaluation

        # 创建数据库会话
        db = get_session()

        try:
            # 创建候选人记录
            candidate_record = CandidateEvaluation(
                resume_url=state.resume_url,
                job_description=state.job_description,
                final_score=state.final_score,
                candidate_level=state.candidate_level,
                skill_score=state.skill_score,
                project_score=state.project_score,
                stability_score=state.stability_score,
                interview_questions=state.interview_questions,
                rejection_letter=state.rejection_letter
            )

            db.add(candidate_record)
            db.commit()
            db.refresh(candidate_record)

            return SaveToDatabaseOutput(candidate_record_id=candidate_record.id)

        except Exception as e:
            db.rollback()
            raise Exception(f"数据库存储失败: {str(e)}")
        finally:
            db.close()

    except Exception as e:
        # 如果数据库操作失败，返回虚拟ID（避免阻塞工作流）
        # 在实际生产环境中，应该记录错误并使用队列重试
        return SaveToDatabaseOutput(candidate_record_id=-1)


# --- 12. 最终报告生成节点 ---
def generate_report_node(state: GenerateReportInput, config: RunnableConfig, runtime: Runtime[Context]) -> GenerateReportOutput:
    """
    title: 最终报告生成
    desc: 汇总所有评估结果，生成最终JSON报告
    integrations:
    """
    ctx = runtime.context

    # 构建最终报告
    final_report = {
        "job_category": state.job_category,
        "summary": {
            "final_score": state.final_score,
            "candidate_level": state.candidate_level,
            "skill_score": state.skill_score,
            "project_score": state.project_score,
            "stability_score": state.stability_score
        },
        "evaluation_details": {
            "skills": {"score": state.skill_score, "weight": "40%"},
            "projects": {"score": state.project_score, "weight": "40%"},
            "stability": {"score": state.stability_score, "weight": "20%"}
        },
        "next_steps": {
            "is_interview_invited": state.candidate_level in ["高潜候选人", "待定候选人"],
            "interview_questions": state.interview_questions if state.interview_questions else [],
            "rejection_letter": state.rejection_letter if state.rejection_letter else ""
        }
    }

    return GenerateReportOutput(final_report=final_report)


# ==================== 条件判断函数 ====================

def should_continue_evaluation(state: dict) -> str:
    """
    title: 是否继续评估
    desc: 根据初筛结果决定是否继续评估
    """
    if state.get("passes_initial_filter", False):
        return "继续评估"
    else:
        return "结束"


# ==================== 条件判断函数（用于分流决策）====================

# 注意：这个函数不在主图中使用，因为加权计算节点已经包含了分流逻辑
# 如果需要单独的条件判断节点，可以在这里定义
