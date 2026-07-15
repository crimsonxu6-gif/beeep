from __future__ import annotations

from typing import Literal

PromptMode = Literal[
    "official", "official_bbox_first", "official_prefill", "beeep_json"
]

OFFICIAL_PREFILL = '{"instance_info":[{"composition_xy":['

COMPOSITION_PREFERENCES = {
    "auto": "由模型自主判断最自然的主体位置，不强制居中或三分构图。",
    "center": "在不破坏画面平衡的前提下，让主要主体倾向画面中心。",
    "thirds_left": "在适合当前场景时，让主要主体倾向左侧三分线。",
    "thirds_right": "在适合当前场景时，让主要主体倾向右侧三分线。",
    "portrait_closeup": "优先形成自然的人像近景，避免不自然地切断面部和关节。",
    "full_body": "优先完整保留人物全身和必要的脚下空间。",
}


def build_official_photographer_prompt(target_ratio: str) -> str:
    """Keep the released photographer-side task wording and output contract."""
    return (
        f"请找出图片中构图最好的区域，请按照{target_ratio}的比例输出bounding box，"
        "并按照(x1,y1),(x2,y2)的格式返回一个bounding box，其中(x1,y1)是左上角的顶点，"
        "(x2,y2)是右下角的顶点。"
    )


def build_official_bbox_first_prompt(target_ratio: str) -> str:
    return (
        build_official_photographer_prompt(target_ratio)
        + "请先输出 composition_xy 字段中的四个坐标，再输出其他说明。"
        + '输出以 {"instance_info":[{"composition_xy":[x1,y1,x2,y2] 开始。'
    )


def build_beeep_json_photographer_prompt(
    target_ratio: str,
    composition_mode: str,
    mode: str = "composition",
    language: str = "zh-CN",
) -> str:
    preference = COMPOSITION_PREFERENCES[composition_mode]
    return (
        f"你正在执行 Beeep 的 photographer-side {mode} 任务。"
        f"目标画幅比例是 {target_ratio}，输出语言标记是 {language}。"
        f"构图偏好：{preference}"
        "判断当前构图属于 keep、refine 或 reject，并给出推荐保留区域。"
        "只输出严格 JSON，不要输出 Markdown、解释或额外文本。"
        '格式：{"decision":"keep | refine | reject",'
        '"bbox_norm":[x1,y1,x2,y2] | null,"confidence":0.0}。'
        "bbox_norm 必须使用 0 到 1 的归一化坐标。"
        "keep 应返回接近完整画面的构图框；reject 可以返回 null。"
    )


def build_photographer_prompt(
    prompt_mode: PromptMode,
    target_ratio: str,
    composition_mode: str,
    mode: str = "composition",
    language: str = "zh-CN",
) -> str:
    if prompt_mode in {"official", "official_prefill"}:
        return build_official_photographer_prompt(target_ratio)
    if prompt_mode == "official_bbox_first":
        return build_official_bbox_first_prompt(target_ratio)
    if prompt_mode == "beeep_json":
        return build_beeep_json_photographer_prompt(
            target_ratio,
            composition_mode,
            mode,
            language,
        )
    raise ValueError(f"Unsupported prompt mode: {prompt_mode}")
