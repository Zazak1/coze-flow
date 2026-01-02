from langgraph.graph import StateGraph, END
from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
    # 报告生成节点输入
    GenerateReportInput,
)
from graphs.node import (
    # 节点函数
    job_category_node,
    document_parse_node,
    privacy_anonymize_node,
    structured_extract_node,
    initial_filter_node,
    skill_match_node,
    project_quality_node,
    background_check_node,
    stability_assess_node,
    weighted_score_node,
    generate_content_node,
    save_to_database_node,
    generate_report_node,
    # 条件判断函数
    should_continue_evaluation,
)


def should_continue_route(state: GlobalState) -> str:
    """
    条件判断函数：是否继续评估

    Args:
        state: 全局状态对象

    Returns:
        路由分支名称
    """
    if state.passes_initial_filter:
        return "继续评估"
    else:
        return "结束"


# 创建状态图，指定输入输出和全局状态
builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# ==================== 添加节点 ====================

# 0. 岗位分类节点
builder.add_node("job_category", job_category_node,
                  metadata={"type": "agent", "llm_cfg": "config/job_category_cfg.json"})

# 第一阶段：数据处理与隐私保护
builder.add_node("document_parse", document_parse_node)
builder.add_node("privacy_anonymize", privacy_anonymize_node,
                  metadata={"type": "agent", "llm_cfg": "config/privacy_anonymize_cfg.json"})
builder.add_node("structured_extract", structured_extract_node,
                  metadata={"type": "agent", "llm_cfg": "config/structured_extract_cfg.json"})

# 第二阶段：硬性门槛筛选
builder.add_node("initial_filter", initial_filter_node)

# 第三阶段：多维度并行评估
builder.add_node("skill_match", skill_match_node,
                  metadata={"type": "agent", "llm_cfg": "config/skill_match_cfg.json"})
builder.add_node("project_quality", project_quality_node,
                  metadata={"type": "agent", "llm_cfg": "config/project_quality_cfg.json"})
builder.add_node("background_check", background_check_node)
builder.add_node("stability_assess", stability_assess_node,
                  metadata={"type": "agent", "llm_cfg": "config/stability_assess_cfg.json"})

# 第四阶段：综合决策
builder.add_node("weighted_score", weighted_score_node)

# 第五阶段：自动化产出
builder.add_node("generate_content", generate_content_node,
                  metadata={"type": "agent", "llm_cfg": "config/generate_content_cfg.json"})
builder.add_node("save_to_database", save_to_database_node)

# 输出阶段
builder.add_node("generate_report", generate_report_node)


# ==================== 添加边 ====================

# 设置入口点：先进行岗位分类
builder.set_entry_point("job_category")

# 岗位分类 -> 文档解析
builder.add_edge("job_category", "document_parse")

# 第一阶段：数据流转
builder.add_edge("document_parse", "privacy_anonymize")
builder.add_edge("privacy_anonymize", "structured_extract")
builder.add_edge("structured_extract", "initial_filter")

# 第二阶段：条件分支（初筛）
builder.add_conditional_edges(
    source="initial_filter",
    path=should_continue_route,
    path_map={
        "继续评估": "start_parallel_evaluation",
        "结束": "generate_report"
    }
)

# 添加一个虚拟节点作为并行评估的起点
def start_parallel_evaluation(state: GlobalState):
    """虚拟节点，用于标记并行评估的开始"""
    return state


builder.add_node("start_parallel_evaluation", start_parallel_evaluation)


# 第三阶段：并行评估
# 从 start_parallel_evaluation 分叉出三个并行分支
builder.add_edge("start_parallel_evaluation", "skill_match")
builder.add_edge("start_parallel_evaluation", "project_quality")
builder.add_edge("start_parallel_evaluation", "background_check")

# 稳定性评估依赖背景调查结果
builder.add_edge("background_check", "stability_assess")

# 并行分支汇聚到加权计算节点
builder.add_edge(["skill_match", "project_quality", "stability_assess"], "weighted_score")

# 第四阶段：综合决策
builder.add_edge("weighted_score", "generate_content")

# 第五阶段：数据存档
builder.add_edge("generate_content", "save_to_database")

# 输出阶段
builder.add_edge("save_to_database", "generate_report")
builder.add_edge("generate_report", END)

# 编译图
main_graph = builder.compile()
