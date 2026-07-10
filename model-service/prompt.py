COMPOSITION_PREFERENCES = {
    "auto": "由模型自主判断最自然的主体位置，不强制居中或三分构图。",
    "center": "在不破坏画面平衡的前提下，让主要主体倾向画面中心。",
    "thirds_left": "在适合当前场景时，让主要主体倾向左侧三分线。",
    "thirds_right": "在适合当前场景时，让主要主体倾向右侧三分线。",
    "portrait_closeup": "优先形成自然的人像近景，避免不自然地切断面部和关节。",
    "full_body": "优先完整保留人物全身和必要的脚下空间。",
}


def build_beeep_photographer_prompt(
    target_ratio: str,
    composition_mode: str,
    mode: str = "composition",
    language: str = "zh-CN",
) -> str:
    preference = COMPOSITION_PREFERENCES[composition_mode]
    # The first paragraph preserves ShutterMuse's released photographer-side task wording.
    return (
        f"请找出图片中构图最好的区域，请按照{target_ratio}的比例输出bounding box，"
        "并按照(x1,y1),(x2,y2)的格式返回一个bounding box，其中(x1,y1)是左上角的顶点，"
        "(x2,y2)是右下角的顶点。\n"
        f"这是 Beeep 的 photographer-side {mode} 任务，输出语言标记为 {language}。"
        "先判断当前画面应 keep、refine 还是 reject。"
        f"构图偏好：{preference}"
        "decision 只允许 keep、refine、reject。只输出一个 JSON 对象，不要输出 Markdown 或解释。"
        '格式示例：{"decision":"refine","bbox_norm":[0.08,0.11,0.91,0.94],"confidence":0.84}。'
        "bbox_norm 必须使用 0 到 1 坐标；keep 使用 [0,0,1,1]；reject 使用 null。"
    )
