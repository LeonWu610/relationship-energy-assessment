"""Verify all major result combinations produce meaningful display output.

This simulates what the JS relationshipStory / sourceStory / mainResultStory
functions would generate for each scenario, without running a browser.
Covers all 16 LIFE_PROFILES plus a summary of unique result combinations.
"""
from stage_a_scoring import score_answers, load_data
from test_stage_a_scoring import LIFE_PROFILES

GROWTH_GATE = {"reciprocityMin": 62, "stabilityMin": 62, "repairMin": 62, "selfPreservationMin": 58, "sustainabilityMin": 62}
PROMINENT_MIN = 38
TIE_GAP = 5
MEDIUM_MARGIN_MIN = 6

DIM_LABELS = {"reciprocity": "双方是否都在实际付出", "stability": "相处是否稳定、让你安心", "repair": "闹矛盾后能否一起解决", "selfPreservation": "你是否还能做自己"}
SRC_LABELS = {"memory": "过去的美好", "potential": "对未来变好的期待", "intermittent": "偶尔出现的热情和高光", "validation": "想确认自己被重视", "loss": "害怕失去这段关系"}
RELATIONSHIP_KEYS = ("reciprocity", "stability", "repair", "selfPreservation")
SOURCE_KEYS = ("memory", "potential", "intermittent", "validation", "loss")


def relationship_story(result):
    rel = result["relationship"]["scores"]
    if not rel:
        return {"title": "目前还不足以判断关系状态", "summary": "有效答案较少，这次先不对关系作整体判断。", "detail": "不需要为了得到结论而勉强补答。"}
    avg = sum(rel.values()) / len(rel)
    lowest = min(rel, key=rel.get)
    strongest = max(rel, key=rel.get)
    stage = result["stage"]
    prefix = "回看这段关系，" if stage == "ended" else ""

    if result["mutualGrowth"]["met"]:
        return {"title": "现实相处中有较多双向支持", "summary": f"{prefix}双方大多愿意用实际行动回应彼此；平时的相处让你心里有底，遇到问题后也能重新沟通。同时，你不需要总是压下自己的感受或放弃原来的生活。", "detail": f"{DIM_LABELS[strongest]}是目前表现更好的一面；接下来可以继续留意{DIM_LABELS[lowest]}。"}
    if avg >= 62:
        return {"title": "这段经历里有不少现实支持" if stage == "ended" else "关系有现实支撑，也有一处需要继续观察", "summary": f"{prefix}这段相处大部分时候能给你支持，但还有一个重要部分没有那么稳。", "detail": f"目前更值得留意的是{DIM_LABELS[lowest]}，看看它是否正在影响你的安心感和日常状态。"}
    if avg >= 50:
        return {"title": "这段经历既有支持，也留下了消耗" if stage == "ended" else "这段关系里，支持与消耗同时存在", "summary": f"{prefix}有些相处让你感到被支持，也有些时候需要你花更多力气才能维持。", "detail": f"最需要回到现实中观察的是{DIM_LABELS[lowest]}：它带来的舒服和压力，哪一种更常出现。"}
    return {"title": "这段经历带来的压力更明显" if stage == "ended" else "这段关系目前更需要照顾你的消耗感", "summary": f"{prefix}你得到的回应和安心感相对有限；出现问题时，双方也未必能一起处理，或者你常常需要压下自己的感受来维持关系。", "detail": f"其中最需要留意的是{DIM_LABELS[lowest]}，以及它是否持续影响你的情绪、生活和选择。"}


def source_story(result):
    sc = result["sourceClassification"]
    src = result["sources"]
    report_id = sc["reportId"]
    status = sc["status"]
    primary = sc["primary"]

    if not src:
        return {"title": "目前还无法判断什么最影响你的投入", "summary": "信息不足，暂不归类。", "report_id": "insufficient_answers"}

    close = [k for k in sorted(SOURCE_KEYS, key=lambda k: -src[k]) if src[max(src, key=src.get)] - src[k] <= TIE_GAP]
    close_names = [SRC_LABELS[k] for k in close]
    primary_names = [SRC_LABELS[k] for k in primary]

    if status == "information_insufficient":
        return {"title": "目前还无法判断什么最影响你的投入", "summary": "信息不足，暂不归类。", "report_id": "insufficient_answers"}
    if status == "fallback":
        return {"title": "没有某一种感受明显左右你的判断", "summary": "过去的美好、对未来变好的期待、偶尔出现的热情、想确认自己被重视，以及害怕失去关系，都没有明显左右你的判断。关系是否适合你，更值得根据双方现实中怎样相处来判断。", "report_id": report_id}
    if status in ("tie", "multiple"):
        return {"title": f"{'与'.join(close_names[:2])}共同影响你的判断", "summary": f"这组完整答案同时指向{'、'.join(close_names)}，不适合压缩成一个标签。", "report_id": report_id}

    margin = src[close[0]] - src[close[1]] if len(close) > 1 else 999
    boundary = margin < MEDIUM_MARGIN_MIN
    title = f"{'、'.join(primary_names)}，更容易影响你现在的判断"
    summary = ""
    if boundary:
        summary += " 不过它与下一项比较接近，更适合作为观察方向，而不是固定标签。"
    if result["sourceClassification"]["unfinished"]:
        summary += " 答案中也出现了对未完成部分的在意。"
    return {"title": title, "summary": summary, "report_id": report_id}


def main_result_story(result, rel, src):
    status = result["sourceClassification"]["status"]
    if status == "information_insufficient" and not result["relationship"]["scores"]:
        return {"title": "这次信息还不足，先不用勉强给关系下结论", "lead": '较多题目与你的情况不重合，或你选择了\u201c不确定 / 不适用\u201d。这不是答错，只是本次答案还不足以支持可靠解释。'}
    if result["mutualGrowth"]["met"] and status == "fallback":
        return {"title": "你更像是在根据现实相处，判断这段关系", "lead": "这段关系目前给了你较多现实支持。过去的美好、对未来的期待、偶尔的高光、想被重视或害怕失去，都没有明显左右你的判断；你更像是在根据双方当下怎样相处来感受这段关系。"}
    if result["mutualGrowth"]["met"]:
        return {"title": "这段关系有现实支撑，也有一种感受在牵动你", "lead": f"{rel['summary']}与此同时，{src['title']}。这两件事可以同时成立。"}
    if status == "fallback":
        return {"title": rel["title"], "lead": f"{rel['summary']}没有某一种特定感受明显左右你的判断，所以更值得看现实中的相处，是否持续符合你的需要。"}
    return {"title": rel["title"], "lead": f"{rel['summary']}同时，{src['title']}；它解释的是你如何理解或留恋这段关系，并不替代对现实相处的判断。"}


data = load_data()

# ── Part 1: All 16 LIFE_PROFILES ──
print("=" * 70)
print("全画像场景验证：16 组生活画像 × 叙事结果")
print("=" * 70)

combos = []  # (growth, srcStatus, stage) signatures for dedup

for i, profile in enumerate(LIFE_PROFILES):
    r = score_answers(data, profile["answers"], profile["stage"])
    rel = relationship_story(r)
    src = source_story(r)
    main = main_result_story(r, rel, src)
    sc = r["sourceClassification"]

    combo = (r["mutualGrowth"]["met"], sc["status"], r["stage"])
    combos.append(combo)

    rel_scores = r["relationship"]["scores"]
    avg_str = f"{sum(rel_scores.values())/len(rel_scores):.1f}" if rel_scores else "N/A"
    src_scores = r["sources"]
    top_src = max(src_scores, key=src_scores.get) if src_scores else "N/A"
    top_val = f"{src_scores[top_src]:.1f}" if src_scores else "N/A"

    print(f"\n{'─' * 60}")
    print(f"📌 L{i+1:02d} {profile['name']}  ({profile['stage']})")
    print(f"   narrative: {profile['narrative']}")
    print(f"   signature: growth={r['mutualGrowth']['met']}, srcStatus={sc['status']}, primary={sc['primary']}")
    print(f"   rel avg={avg_str}, top_source={top_src}({top_val})")
    print(f"")
    print(f"   🏷️  主标题: {main['title']}")
    print(f"   📝  引导句: {main['lead'][:100]}{'...' if len(main['lead'])>100 else ''}")
    print(f"   🏠  现实相处: {rel['title']}")
    print(f"   🔗  什么在影响判断和投入: {src['title']}")

# ── Part 2: Unique combination summary ──
print(f"\n{'=' * 70}")
print("组合签名去重统计")
print("=" * 70)
from collections import Counter
combo_counts = Counter(combos)
for combo, count in sorted(combo_counts.items()):
    print(f"  growth={combo[0]}, srcStatus={combo[1]:<25s} stage={combo[2]}  ×{count}")

unique = len(combo_counts)
print(f"\n共 {len(LIFE_PROFILES)} 个画像，{unique} 种唯一结果组合")

# ── Part 3: Critical-path assertions ──
print(f"\n{'=' * 70}")
print("关键路径断言")
print("=" * 70)

issues = []

# 1. growth+ended should never happen (ended makes growth not applicable)
for i, profile in enumerate(LIFE_PROFILES):
    r = score_answers(data, profile["answers"], profile["stage"])
    if r["stage"] == "ended" and r["mutualGrowth"]["met"]:
        issues.append(f"L{i+1:02d}: ended 场景不应有 mutualGrowth.met=True")

# 2. Every profile must produce a non-empty main title
for i, profile in enumerate(LIFE_PROFILES):
    r = score_answers(data, profile["answers"], profile["stage"])
    rel = relationship_story(r)
    src = source_story(r)
    main = main_result_story(r, rel, src)
    if not main.get("title"):
        issues.append(f"L{i+1:02d}: 主标题为空")
    if not main.get("lead"):
        issues.append(f"L{i+1:02d}: 引导句为空")

# 3. growth=True should imply rel avg >= 62
for i, profile in enumerate(LIFE_PROFILES):
    r = score_answers(data, profile["answers"], profile["stage"])
    if r["mutualGrowth"]["met"] and r["relationship"]["scores"]:
        avg = sum(r["relationship"]["scores"].values()) / len(r["relationship"]["scores"])
        if avg < 62:
            issues.append(f"L{i+1:02d}: growth=True 但 rel avg={avg:.1f} < 62")

# 4. fallback status should mean top source < prominentMin
for i, profile in enumerate(LIFE_PROFILES):
    r = score_answers(data, profile["answers"], profile["stage"])
    if r["sourceClassification"]["status"] == "fallback" and r["sources"]:
        top = max(r["sources"].values())
        if top >= 38:
            issues.append(f"L{i+1:02d}: fallback 但 top source={top:.1f} >= 38")

if issues:
    print("❌ 发现问题：")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("✅ 所有关键路径断言通过")

print(f"\n{'=' * 70}")
print("验证完毕。")
