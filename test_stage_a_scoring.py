#!/usr/bin/env python3
"""阶段 A v1.1：规则单测、叙事先行生活画像和工程边界验证。"""
from __future__ import annotations
import argparse, json, random, tempfile, unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any
from stage_a_scoring import DEFAULT_DATA, RELATIONSHIP_KEYS, SOURCE_KEYS, load_data, read_answers, score_answers, validate_data
DATA=load_data(DEFAULT_DATA); QIDS=[q["id"] for q in DATA["questions"]]

def make(code:str)->dict[str,str]:
    code=code.replace(" ","")
    if len(code)!=28 or any(x not in "ABCDN" for x in code): raise ValueError(f"答案码非法：{code}")
    return {q:("NA" if x=="N" else x) for q,x in zip(QIDS,code)}

def p(pid:str,name:str,narrative:str,stage:str,code:str,required:list[str],allowed:list[str],forbidden:list[str],growth:bool|None,confidence:list[str],unfinished:bool|None)->dict[str,Any]:
    return {"id":pid,"name":name,"narrative":narrative,"stage":stage,"answers":make(code),"expected":{"required":required,"allowed":allowed,"forbidden":forbidden,"growth":growth,"confidence":confidence,"unfinished":unfinished}}

# 画像先写生活叙述，再逐题阅读后手工指定全部答案；未使用任何分数最大化生成器。
LIFE_PROFILES=[
p("L01","恋爱稳定","双方稳定投入，冲突后会回来讨论，也保留各自生活。","ongoing","ABABADBDBAADACBAABADACACAACC",[],["not_prominent","memory"],["intermittent","validation","loss"],True,["low","medium","high"],False),
p("L02","现实压力可修复","工作压力令安排变化，但会说明、补约并共同修复。","ongoing","ABABADBDBAADACBAABADACACAACC",[],["not_prominent","memory"],["intermittent","loss"],True,["low","medium","high"],False),
p("L03","靠过去维持","当下疏远，主要靠过去的主动、默契和承诺解释现在。","ongoing","CCCACACACACACDCCCADCCACCCACA",["memory"],["memory","potential"],["intermittent","validation"],False,["low","medium","high"],False),
p("L04","分手怀念自己","关系结束，怀念共同经历和当时更有生命力的自己，但能生活。","ended","CCCADADCDADADCCACBCDCCACCADC",["memory"],["memory","not_prominent"],["intermittent","validation"],False,["low","medium","high"],False),
p("L05","暧昧等准备好","对方说等状态稳定会确认关系，用户持续等待未来兑现。","ongoing","BDDA BCDCDDDDBDDBDADADBDDBDDB".replace(" ",""),["potential"],["potential"],["memory","intermittent"],False,["medium","high"],False),
p("L06","复合仅口头承诺","提出复合并描绘未来，却没有连续行动或实际修复。","ongoing","BDDBBDDCDDDDBDDBDADADBDDBDBB",["potential"],["potential","intermittent"],["memory"],False,["low","medium","high"],False),
p("L07","冷热暧昧","长时间冷淡后突然热烈，高光常抵消失约和不确定。","ongoing","BAACCBADADBCBDBBCCCBABBBBDDB",["intermittent"],["intermittent","validation"],["memory"],False,["medium","high"],False),
p("L08","断联偶发消息","已经断联，但偶尔一条关心消息会重新点燃投入。","ended","BACACBCDCACCBDBBCCCBACBBBDDB",["intermittent"],["intermittent","memory"],["potential"],False,["low","medium","high"],False),
p("L09","自我价值证明","把对方是否坚定选择自己理解为是否足够好。","ongoing","DCDDBDABDBACBDBBABBBDBBBADAD",["validation"],["validation","loss"],["memory"],False,["low","medium","high"],False),
p("L10","分手比较新伴侣","分手后关注对方新伴侣，想通过被重新选择证明自己。","ended","DCDDBDABDBACBDBBABBBDBBBADAD",["validation"],["validation","loss"],["memory"],False,["low","medium","high"],False),
p("L11","害怕孤独","知道关系不合适，却担心生活空掉、没有支持而停留。","ongoing","DCDDDCACDCCBDADBDDDBADADACCC",["loss"],["loss","validation"],["memory","intermittent"],False,["low","medium","high"],False),
p("L12","复合因怕遇不到","考虑复合主要因为怕以后遇不到合适的人，而非现实改变。","ended","DCDDDCACDCCBDADBDDDBADADACCC",["loss"],["loss","potential"],["intermittent"],False,["low","medium","high"],False),
p("L13","正常悲伤","分手后会怀念和难过，但能区分怀念与重启，也有外部支持。","ended","CBADAAADAAACDCABCBADDCAAACDC",[],["fallback","loss"],["intermittent","validation"],False,["low","medium","high"],False),
p("L14","双来源并列","既留恋过去的好，也等待没完成的共同未来。","ended","CDBBCCCACCBCCDCACBDAACBCCABB",[],["tie","primary"],["intermittent","validation"],False,["low","medium","high"],True),
p("L15","异常低信息","大量题目不适用或不愿作答，不能支持来源或关系结论。","ended","NNNNNNNNNNNNNNNNNNNNABCNNNNN",[],["information_insufficient"],[],False,["insufficient"],False),
p("L16","真实修复复合对照","复合后承诺已转成稳定行动，旧问题能讨论且双方保有边界。","ongoing","ABABADBDBAADACBAABADACACAACC",[],["not_prominent","memory"],["intermittent","loss"],True,["low","medium","high"],False),
]

ENGINEERING_SAMPLES=[{"id":f"E0{i+1}","name":f"全{x}","stage":"ongoing","answers":{q:x for q in QIDS}} for i,x in enumerate("ABCD")]

def check_profile(profile:dict[str,Any],result:dict[str,Any])->list[str]:
    e=profile["expected"]; c=result["sourceClassification"]; labels=set(c["primary"]+[c["status"]]); failures=[]
    for x in e["required"]:
        if x not in labels: failures.append(f"缺少 required {x}")
    if e["allowed"] and not labels.intersection(e["allowed"]): failures.append(f"未落入 allowed {e['allowed']}")
    for x in e["forbidden"]:
        if x in labels: failures.append(f"命中 forbidden {x}")
    if e["growth"] is not None and result["mutualGrowth"]["met"]!=e["growth"]: failures.append("growth 不符")
    if result["confidence"]["level"] not in e["confidence"]: failures.append("confidence 不符")
    if e["unfinished"] is not None and c["unfinished"]!=e["unfinished"]: failures.append("unfinished 不符")
    return failures

def classification_signature(result:dict[str,Any])->tuple[Any,...]:
    c=result["sourceClassification"]; return (result["mutualGrowth"]["met"],c["status"],tuple(c["primary"]),c["unfinished"])

def strict_signature(result:dict[str,Any])->tuple[Any,...]:
    return (*classification_signature(result),result["confidence"]["level"])

def validation()->dict[str,Any]:
    rng=random.Random(20260713); rows=[]; class_stable70=strict_stable70=class_loo_flips=strict_loo_flips=class_option_flips=strict_option_flips=loo_checks=option_checks=0
    for profile in LIFE_PROFILES:
        base=score_answers(DATA,profile["answers"],profile["stage"]); failures=check_profile(profile,base); candidates=[q for q in QIDS if profile["answers"][q]!="NA"]; class_same=[]; strict_same=[]
        for _ in range(100):
            changed=dict(profile["answers"])
            for q in rng.sample(candidates,max(1,round(len(candidates)*.10))): changed[q]=rng.choice([x for x in "ABCD" if x!=changed[q]])
            changed_result=score_answers(DATA,changed,profile["stage"]); class_same.append(classification_signature(changed_result)==classification_signature(base)); strict_same.append(strict_signature(changed_result)==strict_signature(base))
        class_rate=sum(class_same)/100; strict_rate=sum(strict_same)/100; class_stable70+=class_rate>=.70; strict_stable70+=strict_rate>=.70
        for q in candidates:
            changed=dict(profile["answers"]); changed[q]="NA"; changed_result=score_answers(DATA,changed,profile["stage"]); loo_checks+=1; class_loo_flips+=classification_signature(changed_result)!=classification_signature(base); strict_loo_flips+=strict_signature(changed_result)!=strict_signature(base)
            for x in "ABCD":
                changed=dict(profile["answers"]); changed[q]=x; changed_result=score_answers(DATA,changed,profile["stage"]); option_checks+=1; class_option_flips+=classification_signature(changed_result)!=classification_signature(base); strict_option_flips+=strict_signature(changed_result)!=strict_signature(base)
        rows.append({"id":profile["id"],"name":profile["name"],"narrative":profile["narrative"],"stage":profile["stage"],"expected":profile["expected"],"assertionFailures":failures,"passed":not failures,"answers":profile["answers"],"actual":{"growth":base["mutualGrowth"]["met"],"mutualGrowth":base["mutualGrowth"],"relationship":base["relationship"],"sources":base["sources"],"classification":base["sourceClassification"],"confidence":base["confidence"]},"perturbationStableRate":{"classification":round(class_rate,2),"strict":round(strict_rate,2)}})
    engineering=[]
    for sample in ENGINEERING_SAMPLES:
        result=score_answers(DATA,sample["answers"],sample["stage"]); engineering.append({"id":sample["id"],"name":sample["name"],"classification":result["sourceClassification"],"growth":result["mutualGrowth"]["met"],"confidence":result["confidence"]["level"]})
    return {"seed":20260713,"lifeProfileCount":len(rows),"lifeProfilePassed":sum(r["passed"] for r in rows),"engineeringBoundaryCount":len(engineering),"perturbationStableAt70Percent":{"classification":class_stable70,"strict":strict_stable70},"leaveOneOut":{"checks":loo_checks,"classificationFlips":class_loo_flips,"strictFlips":strict_loo_flips},"singleQuestionAllOptionReplacementSensitivity":{"checks":option_checks,"classificationFlips":class_option_flips,"strictFlips":strict_option_flips},"outcomeCounts":dict(Counter(r["actual"]["classification"]["status"] for r in rows)),"lifeProfiles":rows,"engineeringBoundarySamples":engineering}

class ScoringTests(unittest.TestCase):
    def test_schema_and_direction(self): self.assertEqual(validate_data(DATA),[])
    def test_life_profile_assertions(self):
        for profile in LIFE_PROFILES: self.assertEqual(check_profile(profile,score_answers(DATA,profile["answers"],profile["stage"])),[],profile["id"])
    def test_reciprocity_and_sustainability_shape(self):
        r=score_answers(DATA,LIFE_PROFILES[0]["answers"],"ongoing"); self.assertIn("reciprocity",r["relationship"]["scores"]); self.assertEqual(set(r["relationship"]["sustainability"]["subscales"]),{"stability","repair","selfPreservation"})
    def test_normalization_and_recent_weight(self):
        d=deepcopy(DATA); q=d["questions"][0]; a={qid:"NA" for qid in QIDS}; a[q["id"]]="A"; r=score_answers(d,a,"ongoing"); self.assertIsNone(r["relationship"]["scores"])
        a={qid:"A" for qid in QIDS}; r=score_answers(d,a,"ongoing"); self.assertTrue(all(0<=v<=100 for v in r["relationship"]["scores"].values())); self.assertEqual(d["rules"]["recentQuestionWeight"],1.25)
    def test_growth_exact_boundaries(self):
        d=deepcopy(DATA); base=score_answers(d,LIFE_PROFILES[0]["answers"],"ongoing"); scores=base["relationship"]["scores"]
        for key in ("reciprocity","stability","repair","selfPreservation"): d["rules"]["growthGate"][f"{key}Min"]=scores[key]
        d["rules"]["growthGate"]["sustainabilityMin"]=base["relationship"]["sustainability"]["score"]; d["rules"]["growthGate"]["maxStrongRiskAnswers"]=base["strongRiskAnswerCount"]; self.assertTrue(score_answers(d,LIFE_PROFILES[0]["answers"],"ongoing")["mutualGrowth"]["met"])
        d["rules"]["growthGate"]["reciprocityMin"]=scores["reciprocity"]+.01; self.assertFalse(score_answers(d,LIFE_PROFILES[0]["answers"],"ongoing")["mutualGrowth"]["met"])
    def test_confidence_levels(self):
        full=score_answers(DATA,LIFE_PROFILES[2]["answers"],"ongoing"); low=score_answers(DATA,{q:(LIFE_PROFILES[2]["answers"][q] if i<21 else "NA") for i,q in enumerate(QIDS)},"ongoing"); insufficient=score_answers(DATA,LIFE_PROFILES[14]["answers"],"ended"); self.assertIn(full["confidence"]["level"],{"low","medium","high"}); self.assertIn(low["confidence"]["level"],{"low","medium"}); self.assertEqual(insufficient["confidence"]["level"],"insufficient")
    def test_invalid_inputs(self):
        for bad in ("",[],1,{},False):
            with self.assertRaises(ValueError): score_answers(DATA,{"Q01":bad})
        self.assertEqual(score_answers(DATA,{"Q01":None})["answers"]["Q01"],"NA")
    def test_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"a.json"; path.write_text('{"answers":{"Q01":"A","Q01":"B"}}',encoding="utf-8")
            with self.assertRaises(ValueError): read_answers(path)
    def test_unfinished_threshold_boundary(self):
        d=deepcopy(DATA); result=score_answers(d,LIFE_PROFILES[4]["answers"],"ongoing"); weight=result["sourceClassification"]["unfinishedEvidenceWeight"]; d["rules"]["source"]["unfinishedEvidenceWeightMin"]=weight; self.assertTrue(score_answers(d,LIFE_PROFILES[4]["answers"],"ongoing")["sourceClassification"]["unfinished"]); d["rules"]["source"]["unfinishedEvidenceWeightMin"]=weight+.01; self.assertFalse(score_answers(d,LIFE_PROFILES[4]["answers"],"ongoing")["sourceClassification"]["unfinished"])
    def test_two_three_all_ties_and_order(self):
        d=deepcopy(DATA); original=score_answers
        # 通过调整来源计分构造精确二、三、五来源同分，验证分类而非依赖生活画像偶然分数。
        for count,status in ((2,"tie"),(3,"multiple"),(5,"multiple")):
            x=deepcopy(d)
            for q in x["questions"]:
                for o in q["options"]:
                    for i,key in enumerate(SOURCE_KEYS): o["s"][key]=1 if i<count else 0
            r=original(x,{q:"A" for q in QIDS},"ongoing"); self.assertEqual(r["sourceClassification"]["status"],status); self.assertLessEqual(len(r["sourceClassification"]["primary"]),2); self.assertEqual(r["sourceClassification"]["primary"],list(SOURCE_KEYS[:2]))
    def test_stage_filtering_coverage_and_out_of_scene_answers(self):
        for stage in ("ongoing", "ended"):
            applicable=[q for q in DATA["questions"] if q["scene"] in {"all",stage}]
            answers={q["id"]:"A" for q in applicable}
            base=score_answers(DATA,answers,stage)
            self.assertEqual(base["coverage"]["totalQuestionCount"],len(applicable))
            self.assertEqual(base["coverage"]["answeredCount"],len(applicable))
            self.assertEqual(base["coverage"]["totalAnsweredRatio"],1.0)
            outside=next(q for q in DATA["questions"] if q["scene"] not in {"all",stage})
            with_outside=score_answers(DATA,{**answers,outside["id"]:"D"},stage)
            self.assertEqual(classification_signature(base),classification_signature(with_outside))
            self.assertEqual(base["sources"],with_outside["sources"])
            self.assertNotIn(outside["id"],with_outside["answers"])

    def test_na_does_not_score_and_uses_applicable_denominator(self):
        applicable=[q for q in DATA["questions"] if q["scene"] in {"all","ended"}]
        answers={q["id"]:"A" for q in applicable}
        answers[applicable[0]["id"]]="NA"
        result=score_answers(DATA,answers,"ended")
        self.assertEqual(result["coverage"]["answeredCount"],len(applicable)-1)
        self.assertEqual(result["coverage"]["totalQuestionCount"],len(applicable))
        self.assertEqual(result["coverage"]["totalAnsweredRatio"],round((len(applicable)-1)/len(applicable),2))

    def test_ended_relationship_can_compute_but_growth_not_applicable(self):
        for profile in (LIFE_PROFILES[3],LIFE_PROFILES[12]):
            r=score_answers(DATA,profile["answers"],"ended"); self.assertNotEqual(r["relationship"]["status"],"provisional_unavailable"); self.assertFalse(r["mutualGrowth"]["met"]); self.assertFalse(r["mutualGrowth"]["applicable"]); self.assertEqual(r["mutualGrowth"]["notApplicableReason"],"ended_relationship_no_current_growth_judgment")
    def test_report_mapping(self):
        insufficient=score_answers(DATA,LIFE_PROFILES[14]["answers"],"ended")
        self.assertEqual(insufficient["sourceClassification"]["reportId"],"insufficient_answers")
        self.assertIn("sources_not_prominent",DATA["reports"])

    def test_fallback_is_below_prominent_threshold(self):
        result=score_answers(DATA,LIFE_PROFILES[0]["answers"],"ongoing")
        self.assertEqual(result["sourceClassification"]["status"],"fallback")
        self.assertLess(max(result["sources"].values()),DATA["rules"]["source"]["prominentMin"])
        self.assertEqual(len(result["sourceClassification"]["primary"]),1)

    def test_full_answers_can_have_close_sources_without_low_coverage(self):
        result=score_answers(DATA,LIFE_PROFILES[0]["answers"],"ongoing")
        self.assertEqual(result["coverage"]["answeredCount"],result["coverage"]["totalQuestionCount"])
        self.assertEqual(result["coverage"]["totalAnsweredRatio"],1.0)
        self.assertEqual(result["coverage"]["sourceAnsweredRatio"],1.0)
        self.assertEqual(result["sourceClassification"]["status"],"fallback")

    def test_growth_and_source_classification_are_independent(self):
        result=score_answers(DATA,LIFE_PROFILES[0]["answers"],"ongoing")
        self.assertTrue(result["mutualGrowth"]["met"])
        self.assertEqual(result["sourceClassification"]["status"],"fallback")

def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--validation-json",type=Path); args,rest=parser.parse_known_args()
    if args.validation_json: args.validation_json.write_text(json.dumps(validation(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(args.validation_json); return 0
    unittest.main(argv=[__file__,*rest]); return 0
if __name__=="__main__": raise SystemExit(main())
