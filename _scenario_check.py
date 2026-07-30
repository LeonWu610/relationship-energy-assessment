"""验证生活画像的评分路径、结果叙事与跨题洞察。"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from stage_a_scoring import RELATIONSHIP_KEYS, SOURCE_KEYS, load_data, score_answers
from test_stage_a_scoring import LIFE_PROFILES

DATA = load_data()


def interpolate(template: str, values: Mapping[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


def relationship_story(result: Mapping[str, Any]) -> dict[str, Any]:
    config = DATA["resultPresentation"]["relationshipStory"]
    scores = result["relationship"]["scores"]
    if not scores:
        return {**config["insufficient"], "key": "insufficient"}

    average = sum(scores.values()) / len(scores)
    lowest = min(RELATIONSHIP_KEYS, key=lambda key: scores[key])
    strongest = max(RELATIONSHIP_KEYS, key=lambda key: scores[key])
    if (
        result["mutualGrowth"]["met"]
        and average >= config["nourishingAverageMin"]
        and result["strongRiskAnswerCount"] <= config["nourishingMaxStrongRiskAnswers"]
    ):
        story_key = "growth"
    elif average >= config["supportiveAverageMin"]:
        story_key = "supportive"
    elif average >= config["mixedAverageMin"]:
        story_key = "mixed"
    else:
        story_key = "consuming"

    story = config[story_key]
    labels = {key: DATA["dimensions"]["relationship"][key]["label"] for key in RELATIONSHIP_KEYS}
    values = {
        "historyPrefix": config["historyPrefix"][result["stage"]],
        "lowestLabel": labels[lowest],
        "strongestLabel": labels[strongest],
    }
    title = story["title"][result["stage"]] if isinstance(story["title"], dict) else story["title"]
    headline_config = story.get("headline", story["title"])
    headline = headline_config[result["stage"]] if isinstance(headline_config, dict) else headline_config
    return {
        "key": story_key,
        "level": story.get("level"),
        "headline": headline,
        "title": title,
        "summary": interpolate(story["summary"], values),
        "detail": interpolate(story["detail"], values),
    }


def source_story(result: Mapping[str, Any]) -> dict[str, Any]:
    config = DATA["resultPresentation"]["sourceStory"]
    classification = result["sourceClassification"]
    status = classification["status"]
    report_id = config["fallback"]["presentationReportId"] if status == "fallback" else classification["reportId"]
    report = DATA["reports"].get(report_id, DATA["reports"]["insufficient_answers"])
    if status == "information_insufficient":
        return {
            "title": config[status]["title"],
            "summary": interpolate(config[status]["summaryTemplate"], {"reportCore": report["core"]}),
            "report": report,
        }
    if status == "fallback":
        return {"title": config[status]["title"], "summary": config[status]["summary"], "report": report}

    source_labels = {key: DATA["dimensions"]["sources"][key]["label"] for key in SOURCE_KEYS}
    top = max(result["sources"].values())
    close = sorted(SOURCE_KEYS, key=lambda key: (-result["sources"][key], SOURCE_KEYS.index(key)))
    close = [key for key in close if top - result["sources"][key] <= DATA["rules"]["source"]["tieGap"]]
    if status in config["combined"]["statuses"]:
        names = [source_labels[key] for key in close]
        return {
            "title": interpolate(config["combined"]["titleTemplate"], {"closeNamesPair": "与".join(names[:2])}),
            "summary": interpolate(config["combined"]["summaryTemplate"], {"closeNames": "、".join(names)}),
            "report": report,
        }

    names = "、".join(source_labels[key] for key in classification["primary"])
    boundary = result["confidence"]["factors"]["primaryMargin"] < DATA["rules"]["confidence"]["medium"]["primaryMarginMin"]
    return {
        "title": interpolate(config["primary"]["titleTemplate"], {"primaryNames": names}),
        "summary": interpolate(
            config["primary"]["summaryTemplate"],
            {
                "reportCore": report["core"],
                "boundaryNote": config["primary"]["boundaryNote"] if boundary else "",
                "unfinishedNote": config["primary"]["unfinishedNote"] if classification["unfinished"] else "",
            },
        ),
        "report": report,
    }


def main_report_for(result: Mapping[str, Any], relationship: Mapping[str, Any], source: Mapping[str, Any]) -> Mapping[str, Any]:
    if relationship["key"] == "growth" and result["sourceClassification"]["status"] == "fallback":
        return DATA["reports"]["mutual_growth"]
    return source["report"]


def action_footnote(result: Mapping[str, Any]) -> str:
    footnote = DATA["resultPresentation"]["resultDetails"]["actionFootnote"]
    return footnote if isinstance(footnote, str) else footnote[result["stage"]]


def main_result_story(result: Mapping[str, Any], relationship: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, str]:
    config = DATA["resultPresentation"]["mainResultStory"]
    status = result["sourceClassification"]["status"]
    if status == "information_insufficient" and not result["relationship"]["scores"]:
        story = config["insufficient"]
    elif relationship["key"] == "growth" and status == "fallback":
        story = config["growthFallback"]
    elif relationship["key"] == "growth":
        story = config["growth"]
    elif status == "fallback":
        story = config["fallback"]
    else:
        story = config["default"]
    values = {
        "relationshipTitle": relationship.get("headline", relationship["title"]),
        "relationshipSummary": relationship["summary"],
        "sourceTitle": source["title"],
    }
    return {
        "title": story.get("title") or interpolate(story["titleTemplate"], values),
        "lead": story.get("lead") or interpolate(story["leadTemplate"], values),
    }


def select_insights(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    matches = []
    for rule in DATA["resultPresentation"].get("insightRules", []):
        if result["stage"] not in rule["stages"]:
            continue
        groups_match = all(
            sum(result["answers"].get(question_id) in option_ids for question_id, option_ids in group["questions"].items())
            >= group["minimum"]
            for group in rule["evidenceGroups"]
        )
        if groups_match:
            matches.append(rule)
    return sorted(matches, key=lambda rule: -rule["priority"])[:2]


def run_checks() -> list[str]:
    issues: list[str] = []
    forbidden = ("一处", "没有某一种感受", "保留自己", "符合你的需要", "闹矛盾", "局部收缩", "延后表达", "表面恢复平静", "现实依据", "维持原有生活")
    combos = []
    for profile in LIFE_PROFILES:
        result = score_answers(DATA, profile["answers"], profile["stage"])
        relationship = relationship_story(result)
        source = source_story(result)
        main = main_result_story(result, relationship, source)
        report = main_report_for(result, relationship, source)
        text = " ".join((main["title"], main["lead"], relationship["title"], relationship["detail"], source["title"], source["summary"], report["risks"], *report["signals"], *report["actions"], report["share"], action_footnote(result)))
        combos.append((relationship["key"], result["sourceClassification"]["status"], result["stage"]))
        for phrase in forbidden:
            if phrase in text:
                issues.append(f"{profile['id']} 命中禁用表达：{phrase}")
        if not main["title"] or not main["lead"]:
            issues.append(f"{profile['id']} 主结果为空")
        if result["stage"] == "ended" and result["mutualGrowth"]["met"]:
            issues.append(f"{profile['id']} ended 不应命中双向生长")

    real = next(profile for profile in DATA["testPresets"]["items"] if profile["id"] == "preset-08")
    result = score_answers(DATA, real["answers"], real["stage"])
    relationship = relationship_story(result)
    insight_ids = [rule["id"] for rule in select_insights(result)]
    if relationship["key"] != "supportive" or relationship["headline"] != "这段关系带给你的滋养，多过消耗":
        issues.append("真实结果未落入‘这段关系带给你的滋养，多过消耗’")
    if relationship["title"] != "这段关系给你的滋养，多过消耗":
        issues.append("真实结果的分析结论断句不正确")
    if "repair_entry_gap" not in insight_ids:
        issues.append("真实结果未识别‘问题进入对话前的卡点’")
    if "partial_life_contraction" not in insight_ids:
        issues.append("真实结果未识别‘部分安排开始为关系让路’")

    print(f"已检查 {len(LIFE_PROFILES)} 组生活画像，共 {len(Counter(combos))} 种展示组合。")
    print("真实结果：", relationship["headline"], "；洞察：", "、".join(insight_ids))
    return issues


if __name__ == "__main__":
    failures = run_checks()
    if failures:
        print("发现问题：")
        for failure in failures:
            print("-", failure)
        raise SystemExit(1)
    print("所有结果叙事与洞察检查通过。")
