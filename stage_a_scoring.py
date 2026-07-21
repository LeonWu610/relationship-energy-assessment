#!/usr/bin/env python3
"""关系能量测试阶段 A v1.2 透明计分器（仅 Python 标准库）。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_DATA = Path(__file__).with_name("阶段A_题库与报告_v1.0.json")
RELATIONSHIP_KEYS = ("reciprocity", "stability", "repair", "selfPreservation")
SUSTAINABILITY_KEYS = ("stability", "repair", "selfPreservation")
SOURCE_KEYS = ("memory", "potential", "intermittent", "validation", "loss")
VALID_STAGES = ("ongoing", "ended")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON 含重复键：{key}")
        result[key] = value
    return result


def load_data(path: Path | str = DEFAULT_DATA) -> dict[str, Any]:
    try:
        with Path(path).open(encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=_unique_object)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 格式错误：{exc}") from exc


def _round(value: float) -> float:
    return round(value + 1e-12, 2)


def validate_data(data: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schemaVersion", "product", "dimensions", "rules", "scoreKeys", "questions", "reports", "resultPresentation"):
        if key not in data: errors.append(f"顶层缺少 {key}")
    questions = data.get("questions", [])
    if len(questions) != 28: errors.append(f"题目数应为 28，实际为 {len(questions)}")
    if data.get("scoreKeys", {}).get("relationship") != list(RELATIONSHIP_KEYS): errors.append("relationship scoreKeys 不匹配")
    if data.get("scoreKeys", {}).get("sources") != list(SOURCE_KEYS): errors.append("sources scoreKeys 不匹配")
    ids: set[str] = set(); positive_positions: set[str] = set(); negative_positions: set[str] = set()
    for question in questions:
        qid = question.get("id", "?")
        if qid in ids: errors.append(f"题号重复：{qid}")
        ids.add(qid)
        for field in ("stem", "purpose", "ambiguity", "scene", "recent", "relationshipApplicability", "sourceApplicable", "directionCoverage"):
            if field not in question: errors.append(f"{qid} 缺少 {field}")
        if question.get("scene") not in {"all", *VALID_STAGES}: errors.append(f"{qid} scene 非法")
        coverage = question.get("directionCoverage", {})
        if coverage.get("method") != "direct_option_scoring": errors.append(f"{qid} 未声明选项级直接方向计分")
        options = question.get("options", [])
        if len(options) != 4 or {o.get("id") for o in options} != set("ABCD"): errors.append(f"{qid} 必须恰有 A/B/C/D")
        actual_pos=[]; actual_neg=[]; actual_signal=[]
        for option in options:
            oid=option.get("id", "?"); rs=option.get("r", {}); ss=option.get("s", {})
            if set(rs) != set(RELATIONSHIP_KEYS): errors.append(f"{qid}/{oid} 关系分键不完整")
            if set(ss) != set(SOURCE_KEYS): errors.append(f"{qid}/{oid} 来源分键不完整")
            if any(type(v) is not int or not -2 <= v <= 2 for v in rs.values()): errors.append(f"{qid}/{oid} 关系分超界")
            if any(type(v) is not int or not 0 <= v <= 2 for v in ss.values()): errors.append(f"{qid}/{oid} 来源分超界")
            if sum(rs.values()) >= 3: actual_pos.append(oid); positive_positions.add(oid)
            if sum(rs.values()) <= -3: actual_neg.append(oid); negative_positions.add(oid)
            if sum(ss.values()) > 0: actual_signal.append(oid)
        if coverage.get("positivePositions") != actual_pos or coverage.get("negativePositions") != actual_neg or coverage.get("sourceSignalPositions") != actual_signal: errors.append(f"{qid} directionCoverage 与分值不一致")
        applicability=question.get("relationshipApplicability", [])
        if not isinstance(applicability, list) or not set(applicability)<=set(VALID_STAGES) or len(applicability)!=len(set(applicability)): errors.append(f"{qid} relationshipApplicability 非法")
        scene=question.get("scene")
        shown_stages=set(VALID_STAGES) if scene=="all" else {scene}
        stem_by_stage=question.get("stemByStage",{})
        if stem_by_stage and (not isinstance(stem_by_stage,dict) or not set(stem_by_stage)<=shown_stages or any(not isinstance(value,str) or not value.strip() for value in stem_by_stage.values())): errors.append(f"{qid} stemByStage 非法")
        recent_stages=question.get("recentStages",list(shown_stages) if question.get("recent") else [])
        if not isinstance(recent_stages,list) or not set(recent_stages)<=shown_stages or (recent_stages and not question.get("recent")): errors.append(f"{qid} recentStages 非法")
        if not set(applicability)<=shown_stages: errors.append(f"{qid} relationshipApplicability 超出展示场景")
        if type(question.get("sourceApplicable")) is not bool: errors.append(f"{qid} sourceApplicable 必须是布尔值")
        if not applicability and any(any(option.get("r", {}).values()) for option in options): errors.append(f"{qid} 不进入关系层但仍含关系分")
        if question.get("sourceApplicable") is False and any(any(option.get("s", {}).values()) for option in options): errors.append(f"{qid} 不进入来源层但仍含来源分")
    if positive_positions != set("ABCD"): errors.append("正向内容位置未覆盖 A/B/C/D")
    if negative_positions != set("ABCD"): errors.append("负向内容位置未覆盖 A/B/C/D")
    rules=data.get("rules", {})
    for path in (("growthGate","reciprocityMin"),("growthGate","relationshipAverageMin"),("growthGate","relationshipCoverageMin"),("growthGate","applicableStages"),("growthGate","endedNotApplicableReason"),("coverage","totalAnsweredRatioMin"),("coverage","relationshipMinApplicableQuestionsByStage"),("source","unfinishedEvidenceWeightMin"),("source","practicalEvidenceWeightMin"),("confidence","high"),("confidence","medium")):
        if path[0] not in rules or path[1] not in rules.get(path[0], {}): errors.append(f"规则缺少 {path[0]}.{path[1]}")
    growth_rule=rules.get("growthGate", {})
    if growth_rule.get("applicableStages") != ["ongoing"]: errors.append("双向生长只能适用于 ongoing")
    if growth_rule.get("endedNotApplicableReason") != "ended_relationship_no_current_growth_judgment": errors.append("ended 双向生长不适用原因不正确")
    required={"memory_supply","potential_wait","intermittent_reward","self_proof","loss_fear","mutual_growth","mixed","sources_not_prominent","insufficient_answers"}
    if required-set(data.get("reports", {})): errors.append(f"缺少报告：{sorted(required-set(data.get('reports', {})))}")
    safety_values=[r.get("safety","") for r in data.get("reports",{}).values()]
    if any("当地紧急服务" not in text for text in safety_values): errors.append("报告安全提示不完整")
    presentation=data.get("resultPresentation",{})
    relationship_story=presentation.get("relationshipStory",{})
    for key in ("nourishingAverageMin","nourishingMaxStrongRiskAnswers","supportiveAverageMin","mixedAverageMin"):
        if key not in relationship_story: errors.append(f"结果规则缺少 relationshipStory.{key}")
    if growth_rule.get("relationshipAverageMin") != relationship_story.get("nourishingAverageMin"): errors.append("双向生长与明显滋养的平均分门槛不一致")
    if growth_rule.get("maxStrongRiskAnswers") != relationship_story.get("nourishingMaxStrongRiskAnswers"): errors.append("双向生长与明显滋养的强风险门槛不一致")
    question_ids={q.get("id") for q in questions}
    insight_ids:set[str]=set()
    for rule in presentation.get("insightRules",[]):
        rule_id=rule.get("id","?")
        if rule_id in insight_ids: errors.append(f"洞察规则重复：{rule_id}")
        insight_ids.add(rule_id)
        if not rule.get("evidenceGroups") or not rule.get("title") or not rule.get("body"): errors.append(f"洞察规则不完整：{rule_id}")
        if not set(rule.get("stages",[]))<=set(VALID_STAGES): errors.append(f"洞察规则场景非法：{rule_id}")
        for group in rule.get("evidenceGroups",[]):
            if group.get("minimum",0)<1 or group.get("minimum",0)>len(group.get("questions",{})): errors.append(f"洞察规则证据门槛非法：{rule_id}")
            unknown_questions=set(group.get("questions",{}))-question_ids
            if unknown_questions: errors.append(f"洞察规则引用未知题目：{rule_id}/{sorted(unknown_questions)}")
            if any(not set(options)<=set("ABCD") for options in group.get("questions",{}).values()): errors.append(f"洞察规则答案非法：{rule_id}")
    return errors


def _normalize(raw: float, minimum: float, maximum: float) -> float:
    return _round(50.0 if maximum == minimum else 100*(raw-minimum)/(maximum-minimum))


def _confidence(rules: Mapping[str, Any], total: float, source: float, scene: float, margin: float, threshold_distance: float, computable: bool) -> dict[str, Any]:
    factors={"totalCoverage":_round(total),"sourceCoverage":_round(source),"applicableSceneCoverage":_round(scene),"primaryMargin":_round(margin),"nearestKeyThresholdDistance":_round(threshold_distance)}
    if not computable: level="insufficient"
    else:
        def meets(name: str) -> bool:
            x=rules["confidence"][name]
            return total>=x["totalCoverageMin"] and source>=x["sourceCoverageMin"] and scene>=x["sceneCoverageMin"] and margin>=x["primaryMarginMin"] and threshold_distance>=x["thresholdDistanceMin"]
        level="high" if meets("high") else "medium" if meets("medium") else "low"
    return {"level":level,"factors":factors,"explanation":"由总答题覆盖、来源覆盖、适用场景覆盖、主次分差和最近关键阈值距离共同决定；任一短板会降级。"}


def score_answers(data: Mapping[str, Any], answers: Mapping[str, Any], stage: str="ongoing") -> dict[str, Any]:
    if not isinstance(answers, Mapping): raise ValueError("answers 必须是题号到答案的对象")
    if stage not in VALID_STAGES: raise ValueError("stage 必须是 ongoing 或 ended")
    rules=data["rules"]; questions=data["questions"]; qmap={q["id"]:q for q in questions}
    unknown=sorted(set(answers)-set(qmap))
    if unknown: raise ValueError(f"未知题号：{', '.join(unknown)}")
    applicable_questions=[q for q in questions if q["scene"] in {"all", stage}]
    applicable_ids={q["id"] for q in applicable_questions}
    normalized: dict[str,str]={}
    for qid,value in answers.items():
        if qid not in applicable_ids: continue
        if value is None: normalized[qid]="NA"; continue
        if not isinstance(value,str): raise ValueError(f"{qid} 答案必须是字符串或 None")
        if value == "": raise ValueError(f"{qid} 答案不能为空字符串")
        value=value.upper()
        if value not in {"A","B","C","D","NA"}: raise ValueError(f"{qid} 的答案必须是 A/B/C/D/NA")
        normalized[qid]=value
    rel_raw={k:0.0 for k in RELATIONSHIP_KEYS}; rel_min={k:0.0 for k in RELATIONSHIP_KEYS}; rel_max={k:0.0 for k in RELATIONSHIP_KEYS}
    src_raw={k:0.0 for k in SOURCE_KEYS}; src_max={k:0.0 for k in SOURCE_KEYS}
    answered=source_answered=relationship_answered=strong=0; unfinished_weight=practical_weight=0.0
    relationship_applicable=sum(stage in q["relationshipApplicability"] for q in applicable_questions)
    source_applicable=sum(bool(q["sourceApplicable"]) for q in applicable_questions)
    output_answers: dict[str,str]={}
    for q in applicable_questions:
        qid=q["id"]; answer=normalized.get(qid,"NA"); output_answers[qid]=answer
        if answer=="NA": continue
        answered+=1; source_answered+=int(q["sourceApplicable"]); option=next(o for o in q["options"] if o["id"]==answer)
        recent_stages=q.get("recentStages", VALID_STAGES)
        weight=float(rules["recentQuestionWeight"] if q["recent"] and stage in recent_stages else 1.0)
        if q["sourceApplicable"]:
            for key in SOURCE_KEYS:
                src_raw[key]+=option["s"][key]*weight; src_max[key]+=max(o["s"][key] for o in q["options"])*weight
            if "unfinished" in option.get("tags",[]): unfinished_weight+=weight
            if "practical_constraint" in option.get("tags",[]): practical_weight+=weight
        if stage in q["relationshipApplicability"]:
            relationship_answered+=1; strong+=int(any(option["r"][k]<=-2 for k in RELATIONSHIP_KEYS))
            for key in RELATIONSHIP_KEYS:
                rel_raw[key]+=option["r"][key]*weight; rel_min[key]+=min(o["r"][key] for o in q["options"])*weight; rel_max[key]+=max(o["r"][key] for o in q["options"])*weight
    applicable_count=len(applicable_questions)
    total_cov=answered/applicable_count if applicable_count else 0
    source_cov=source_answered/source_applicable if source_applicable else 0
    scene_cov=relationship_answered/relationship_applicable if relationship_applicable else 0
    coverage=rules["coverage"]
    source_computable=source_cov>=coverage["sourceAnsweredRatioMin"]
    relationship_min=coverage.get("relationshipMinApplicableQuestionsByStage",{}).get(stage,coverage["relationshipMinApplicableQuestions"])
    relationship_computable=relationship_answered>=relationship_min and scene_cov>=coverage["relationshipApplicableRatioMin"]
    relationship={k:_normalize(rel_raw[k],rel_min[k],rel_max[k]) for k in RELATIONSHIP_KEYS} if relationship_computable else None
    relationship_average=_round(sum(relationship.values())/len(RELATIONSHIP_KEYS)) if relationship else None
    sustainability=_round(sum(relationship[k] for k in SUSTAINABILITY_KEYS)/3) if relationship else None
    sources={k:_round(0 if src_max[k]==0 else 100*src_raw[k]/src_max[k]) for k in SOURCE_KEYS} if source_computable else None
    growth=False
    historically_nourishing=False
    growth_reason = None
    g=rules["growthGate"]
    relationship_story=data["resultPresentation"]["relationshipStory"]
    nourishing_evidence=bool(
        relationship
        and scene_cov>=g["relationshipCoverageMin"]
        and relationship_average>=g["relationshipAverageMin"]
        and relationship["reciprocity"]>=g["reciprocityMin"]
        and relationship["stability"]>=g["stabilityMin"]
        and relationship["repair"]>=g["repairMin"]
        and relationship["selfPreservation"]>=g["selfPreservationMin"]
        and sustainability>=g["sustainabilityMin"]
        and strong<=g["maxStrongRiskAnswers"]
    )
    if stage not in g["applicableStages"]:
        growth_reason=g["endedNotApplicableReason"]
        historically_nourishing=nourishing_evidence
    elif relationship:
        growth=nourishing_evidence
    source_rule=rules["source"]; primary:list[str]=[]; secondary:list[str]=[]; ranked:list[str]=[]; margin=top=0.0; source_status="information_insufficient"; report_id="insufficient_answers"
    if sources:
        order=source_rule["fixedOrder"]; ranked=sorted(SOURCE_KEYS,key=lambda k:(-sources[k],order.index(k))); top=sources[ranked[0]]; margin=top-sources[ranked[1]]
        near=[k for k in ranked if top-sources[k]<=source_rule["tieGap"]]
        if top<source_rule["prominentMin"]:
            if top==0: source_status="not_prominent"; report_id="sources_not_prominent"
            else: source_status="fallback"; primary=[ranked[0]]; report_id=data["dimensions"]["sources"][primary[0]]["resultId"]
        elif len(near)>=3: source_status="multiple"; primary=near[:source_rule["maxPrimarySources"]]; report_id="mixed"
        elif len(near)==2: source_status="tie"; primary=near; report_id="mixed"
        else:
            source_status="primary"; primary=[ranked[0]]; report_id=data["dimensions"]["sources"][primary[0]]["resultId"]
            secondary=[k for k in ranked[1:] if sources[k]>=source_rule["prominentMin"] and top-sources[k]<=source_rule["secondaryGap"]][:1]
    source_decision_distances=[]
    if sources:
        source_decision_distances.append(abs(top-source_rule["prominentMin"]))
        if source_status=="primary": source_decision_distances += [abs(margin-source_rule["tieGap"]),abs(margin-source_rule["secondaryGap"])]
        elif source_status=="tie":
            source_decision_distances.append(abs(margin-source_rule["tieGap"]))
            if len(ranked)>=3: source_decision_distances.append(abs((top-sources[ranked[2]])-source_rule["tieGap"]))
        elif source_status=="multiple" and len(ranked)>=3:
            source_decision_distances.append(abs((top-sources[ranked[2]])-source_rule["tieGap"]))
    thresholds=list(source_decision_distances)
    if relationship:
        gate=rules["growthGate"]
        thresholds += [abs(relationship[key]-gate[f"{key}Min"]) for key in RELATIONSHIP_KEYS]
        thresholds.append(abs(sustainability-gate["sustainabilityMin"]))
        thresholds += [abs(relationship_average-relationship_story[key]) for key in ("mixedAverageMin","supportiveAverageMin","nourishingAverageMin")]
    threshold_distance=min(thresholds) if thresholds else 0.0
    confidence_margin=margin if source_status=="primary" else 100.0
    confidence=_confidence(rules,total_cov,source_cov,scene_cov,confidence_margin,threshold_distance,source_computable or relationship_computable)
    relationship_boundary_distance=min((abs(relationship_average-x) for x in (data["resultPresentation"]["relationshipStory"]["mixedAverageMin"],data["resultPresentation"]["relationshipStory"]["supportiveAverageMin"],data["resultPresentation"]["relationshipStory"]["nourishingAverageMin"])),default=100.0) if relationship else None
    source_boundary_distance=min(source_decision_distances) if source_decision_distances else None
    return {"ruleVersion":rules["version"],"stage":stage,"coverage":{"answeredCount":answered,"totalQuestionCount":applicable_count,"totalAnsweredRatio":_round(total_cov),"sourceApplicableCount":source_applicable,"sourceAnsweredCount":source_answered,"sourceAnsweredRatio":_round(source_cov),"relationshipApplicableCount":relationship_applicable,"relationshipAnsweredCount":relationship_answered,"relationshipApplicableRatio":_round(scene_cov),"relationshipMinRequired":relationship_min},"relationship":{"status":"final" if relationship_computable else "provisional_unavailable","scores":relationship,"average":relationship_average,"reciprocity":relationship["reciprocity"] if relationship else None,"nourishingEvidence":nourishing_evidence,"historicallyNourishing":historically_nourishing,"sustainability":{"score":sustainability,"subscales":{k:relationship[k] for k in SUSTAINABILITY_KEYS} if relationship else None}},"strongRiskAnswerCount":strong,"mutualGrowth":{"met":growth,"applicable":stage in g["applicableStages"],"reportId":"mutual_growth" if growth else None,"notApplicableReason":growth_reason},"sources":sources,"sourceClassification":{"status":source_status,"primary":primary,"secondary":secondary,"reportId":report_id,"unfinished":unfinished_weight>=source_rule["unfinishedEvidenceWeightMin"] if source_computable else False,"unfinishedEvidenceWeight":_round(unfinished_weight),"unfinishedThreshold":source_rule["unfinishedEvidenceWeightMin"],"practicalContext":practical_weight>=source_rule["practicalEvidenceWeightMin"] if source_computable else False,"practicalEvidenceWeight":_round(practical_weight),"practicalThreshold":source_rule["practicalEvidenceWeightMin"],"fixedOrderNotice":source_rule["fixedOrderNotice"]},"boundaries":{"relationshipDistance":_round(relationship_boundary_distance) if relationship_boundary_distance is not None else None,"relationshipNear":relationship_boundary_distance is not None and relationship_boundary_distance<3,"sourceDistance":_round(source_boundary_distance) if source_boundary_distance is not None else None,"sourceNear":source_boundary_distance is not None and source_boundary_distance<3},"confidence":confidence,"answers":output_answers,"disclaimer":data["product"]["nature"],"calibrationNotice":data["product"]["scoringNotice"]}


def read_answers(path: Path | str) -> tuple[Mapping[str, Any], str]:
    try:
        with Path(path).open(encoding="utf-8") as handle: payload=json.load(handle,object_pairs_hook=_unique_object)
    except json.JSONDecodeError as exc: raise ValueError(f"答案 JSON 格式错误：{exc}") from exc
    if not isinstance(payload,dict): raise ValueError("答案 JSON 必须是对象")
    stage=payload.get("stage","ongoing")
    answers=payload.get("answers",payload)
    if "answers" in payload and not isinstance(answers,dict): raise ValueError("answers 必须是对象")
    if "answers" not in payload: stage="ongoing"
    return answers,stage


def main(argv: Sequence[str]|None=None)->int:
    parser=argparse.ArgumentParser(); parser.add_argument("answers",nargs="?",type=Path); parser.add_argument("--data",type=Path,default=DEFAULT_DATA); parser.add_argument("--validate",action="store_true"); parser.add_argument("--pretty",action="store_true"); args=parser.parse_args(argv)
    data=load_data(args.data); errors=validate_data(data)
    if errors: print(json.dumps({"valid":False,"errors":errors},ensure_ascii=False,indent=2)); return 1
    if args.validate: print(json.dumps({"valid":True,"questions":len(data["questions"]),"schemaVersion":data["schemaVersion"]},ensure_ascii=False)); return 0
    if args.answers is None: raise SystemExit("请提供答案 JSON 文件，或使用 --validate")
    answers,stage=read_answers(args.answers); print(json.dumps(score_answers(data,answers,stage),ensure_ascii=False,indent=2 if args.pretty else None)); return 0
if __name__=="__main__": raise SystemExit(main())
