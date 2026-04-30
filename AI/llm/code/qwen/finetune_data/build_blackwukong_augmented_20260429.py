import json
import random
from collections import Counter
from pathlib import Path


_DATA_DIR = Path(__file__).resolve().parent


BASE_PATH = _DATA_DIR / "blackwukong_base_20260429.jsonl"
OUT_PATH = _DATA_DIR / "blackwukong_augmented_20260429.jsonl"
KNOWLEDGE_UNITS_PATH = _DATA_DIR / "blackwukong_knowledge_units_20260429.json"
REPORT_PATH = _DATA_DIR / "blackwukong_augmented_20260429_report.json"
WORKFLOW_PATH = _DATA_DIR / "blackwukong_augmented_workflow_20260429.md"

random.seed(20260429)


def load_base_entries():
    entries = []
    with BASE_PATH.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            obj["source_id"] = idx
            obj["task"] = "qa"
            obj["category"] = categorize(idx)
            obj["answer_length"] = classify_answer_length(obj["output"])
            entries.append(obj)
    return entries


def select_base_training_entries(base_entries):
    quotas = {
        "basic_facts": 22,
        "roles_and_bosses": 23,
        "story_flow": 45,
        "items_and_equipment": 23,
        "systems_and_mechanics": 37,
        "achievements_and_lists": 20,
    }
    selected = []
    counts = Counter()
    for entry in base_entries:
        category = entry["category"]
        if counts[category] < quotas[category]:
            selected.append(entry)
            counts[category] += 1
    return selected


def categorize(source_id):
    if 1 <= source_id <= 22:
        return "basic_facts"
    if 23 <= source_id <= 45:
        return "roles_and_bosses"
    if 46 <= source_id <= 97:
        return "story_flow"
    if 98 <= source_id <= 120:
        return "items_and_equipment"
    if 121 <= source_id <= 161:
        return "systems_and_mechanics"
    return "achievements_and_lists"


def classify_answer_length(text):
    length = len(text)
    if length <= 24:
        return "short"
    if length <= 70:
        return "medium"
    return "long"


def make_entry(instruction, output, task, category, source_refs):
    return {
        "instruction": instruction,
        "output": output,
        "task": task,
        "category": category,
        "source_refs": source_refs,
        "answer_length": classify_answer_length(output),
    }


def rewrite_question(question, style_idx):
    q = question.rstrip("？?")
    replacements = [
        ("《黑神话：悟空》", "这款游戏"),
        ("《黑神话：悟空》", "黑神话这作"),
        ("玩家", "游戏里玩家"),
        ("天命人", "主角天命人"),
    ]
    q_variant = q
    for old, new in replacements:
        if old in q_variant:
            q_variant = q_variant.replace(old, new, 1)
            break

    patterns = [
        lambda s: f"按资料看，{s}？",
        lambda s: f"我有点记不清了，{s}？",
        lambda s: f"换个说法问一下，{s}？",
        lambda s: f"请直接回答：{s}？",
        lambda s: f"如果只看给定资料，{s}？",
        lambda s: f"根据文档内容，{s}？",
        lambda s: f"{s}这一点原文是怎么说的？",
        lambda s: f"能不能简单说下，{s}？",
    ]
    return patterns[style_idx % len(patterns)](q_variant)


def rewrite_output(output, style_idx):
    text = output.rstrip("。")
    patterns = [
        lambda s: f"{s}。",
        lambda s: f"原文提到，{s}。",
        lambda s: f"按资料所述，{s}。",
        lambda s: f"就给定内容来看，{s}。",
        lambda s: f"资料里明确写到，{s}。",
    ]
    return patterns[style_idx % len(patterns)](text)


def build_variant_facts(base_entries):
    variants = []
    chosen = base_entries[:120]
    for idx, entry in enumerate(chosen):
        instruction = rewrite_question(entry["instruction"], idx)
        output = rewrite_output(entry["output"], idx)
        variants.append(
            make_entry(
                instruction=instruction,
                output=output,
                task="qa_variant",
                category=entry["category"],
                source_refs=[entry["source_id"]],
            )
        )
    return variants


def build_positive_judgments(base_entries):
    judgments = []
    chosen = [e for e in base_entries if e["source_id"] <= 160][:35]
    prompts = [
        "根据资料判断，这句话是否符合原文：{statement}",
        "下面这句说法对不对：{statement}",
        "只根据给定文档判断，以下表述是否准确：{statement}",
        "请核对这句话是否与原文一致：{statement}",
        "这句话和资料内容一致吗：{statement}",
    ]
    for idx, entry in enumerate(chosen):
        statement = entry["output"].rstrip("。") + "。"
        instruction = prompts[idx % len(prompts)].format(statement=statement)
        output = f"符合原文。{rewrite_output(entry['output'], idx + 1)}"
        judgments.append(
            make_entry(
                instruction=instruction,
                output=output,
                task="judgment",
                category=entry["category"],
                source_refs=[entry["source_id"]],
            )
        )
    return judgments


def build_negative_judgments():
    negatives = [
        ("根据资料判断，这句话是否符合原文：《黑神话：悟空》由浙江出版集团数字传媒有限公司开发。", "不符合原文。原文说明《黑神话：悟空》由杭州游科互动科技有限公司开发，浙江出版集团数字传媒有限公司出版。", "basic_facts", [1, 2]),
        ("下面这句说法对不对：《黑神话：悟空》首发只登录了PS5平台。", "不符合原文。原文说明该作于2024年8月20日正式登陆PC、PS5平台。", "basic_facts", [8]),
        ("只根据给定文档判断，以下表述是否准确：媒体通常把《黑神话：悟空》称作日本首款3A游戏。", "不符合原文。原文提到该作通常被媒体称为“中国首款3A游戏”。", "basic_facts", [9]),
        ("请核对这句话是否与原文一致：天命人是猪八戒。", "不符合原文。原文说明天命人是花果山上的一只猴子。", "roles_and_bosses", [23]),
        ("这句话和资料内容一致吗：游戏中共有三类角色，分别是小妖、妖王、人物。", "不符合原文。原文说明游戏中共有四类角色，分别是小妖、头目、妖王、人物。", "roles_and_bosses", [25]),
        ("根据资料判断，这句话是否符合原文：黑熊精是黑风大王的第一阶段。", "不符合原文。原文说明黑熊精是黑风大王的第二阶段。", "roles_and_bosses", [35]),
        ("下面这句说法对不对：黄风大圣的风墙需要辟火罩来破除。", "不符合原文。原文说明可使用法宝“定风珠”破除黄风大圣的风墙。", "roles_and_bosses", [43]),
        ("只根据给定文档判断，以下表述是否准确：序章中是猪八戒讲述了孙悟空陨落之战。", "不符合原文。原文说明序章开头借老猴子之口，讲述当年孙悟空陨落之战。", "story_flow", [46]),
        ("请核对这句话是否与原文一致：第一回“火照黑云”的地点是黄风岭。", "不符合原文。原文说明第一回“火照黑云”的地点为黑风山。", "story_flow", [51]),
        ("这句话和资料内容一致吗：第二回中天命人学会了定身术和聚形散气。", "不符合原文。原文说明第二回中天命人学会了铜头铁臂和身外身法。", "story_flow", [60]),
        ("根据资料判断，这句话是否符合原文：第三回最终是在黑风洞击败黄眉。", "不符合原文。原文说明第三回最后在小雷音寺击败了黄眉。", "story_flow", [71]),
        ("下面这句说法对不对：第四回通关后获得的大圣六根之一是“耳听怒”。", "不符合原文。原文说明通关第四回获取的大圣六根之一是“舌尝思”。", "story_flow", [77]),
        ("只根据给定文档判断，以下表述是否准确：第五回中小狐狸的真实身份是牛魔王。", "不符合原文。原文说明第五回中小狐狸现出真面目，原来为红孩儿假扮。", "story_flow", [82]),
        ("请核对这句话是否与原文一致：第六回的地点在火焰山。", "不符合原文。原文说明第六回“未竟”的地点为花果山。", "story_flow", [87]),
        ("这句话和资料内容一致吗：没有完成隐藏剧情也会进入结局二。", "不符合原文。原文说明若没有完成相关隐藏剧情，在击败大圣残躯后会进入结局一。", "story_flow", [93]),
        ("根据资料判断，这句话是否符合原文：铜云棒需要击败黄眉后解锁。", "不符合原文。原文说明铜云棒在购买豪华版后解锁，可在土地庙的谢礼菜单中领取。", "items_and_equipment", [102]),
        ("下面这句说法对不对：兽棍·熊罴的材料来自白衣秀士。", "不符合原文。原文说明击败黑熊精后获得材料“烈火乌金”即可解锁兽棍·熊罴的铸造。", "items_and_equipment", [105]),
        ("只根据给定文档判断，以下表述是否准确：楮白枪会提高所有立棍招式的伤害。", "不符合原文。原文说明楮白枪会在轻棍连招中融入枪术，增加所有戳棍招式的伤害。", "items_and_equipment", [116]),
        ("请核对这句话是否与原文一致：《黑神话：悟空》提供格挡功能作为主要防御方式。", "不符合原文。原文说明该作没有格挡功能，主要防御方式是通过翻滚进行闪避。", "systems_and_mechanics", [126, 127]),
        ("这句话和资料内容一致吗：游戏中等级最高可达到100级。", "不符合原文。原文说明等级最高可达到342级。", "systems_and_mechanics", [130]),
        ("根据资料判断，这句话是否符合原文：法术耗尽后只能靠击败敌人恢复。", "不符合原文。原文说明法术耗尽后，玩家可选择在土地庙恢复法力。", "systems_and_mechanics", [135]),
        ("下面这句说法对不对：变身成妖怪后不会获得独立血条。", "不符合原文。原文说明玩家在变身妖怪后会获得独立的血条。", "systems_and_mechanics", [147]),
        ("只根据给定文档判断，以下表述是否准确：化身技发动后会获得独立血条。", "不符合原文。原文说明化身技变身后并不会获得独立的血条，受到伤害依然扣的是玩家自身的血量。", "systems_and_mechanics", [155]),
        ("请核对这句话是否与原文一致：再战系统只提供连战，不提供复战。", "不符合原文。原文说明玩家可以自行决定复战（单挑）或者是连战（车轮战）。", "systems_and_mechanics", [158]),
        ("这句话和资料内容一致吗：“下降尘凡第一难”的达成条件是击败灵虚子。", "不符合原文。原文说明“下降尘凡第一难”的达成条件是击败“序章-二郎显圣真君”。", "achievements_and_lists", [162]),
        ("根据资料判断，这句话是否符合原文：“禅院逢友第九难”要求找到隐·观音禅院。", "不符合原文。原文说明“禅院逢友第九难”的达成条件是击败“金池长老”。", "achievements_and_lists", [169, 170]),
        ("下面这句说法对不对：“黄金引路十九难”对应的是进入梅山。", "不符合原文。原文说明“黄金引路十九难”的达成条件是找到“隐·斯哈里国”。", "achievements_and_lists", [180]),
        ("只根据给定文档判断，以下表述是否准确：“胡说胡说三十八难”需要击败右手虫。", "不符合原文。原文说明“胡说胡说三十八难”的达成条件是击败“黄眉”。", "achievements_and_lists", [199, 200]),
        ("请核对这句话是否与原文一致：“六根齐聚七十四难”的达成条件是解锁全部游记。", "不符合原文。原文说明“六根齐聚七十四难”的达成条件是开启二周目。", "achievements_and_lists", [218]),
        ("这句话和资料内容一致吗：“夹枪带棒八十难”要求获得所有防具。", "不符合原文。原文说明“夹枪带棒八十难”的达成条件是获得所有武器。", "achievements_and_lists", [223, 224]),
    ]
    return [make_entry(i, o, "judgment", c, r) for i, o, c, r in negatives]


def build_compare_entries():
    data = [
        (
            "对比一下劈棍、立棍和戳棍各自的主要特点。",
            "三者都属于天命人的棍法战斗方式。劈棍侧重通过轻击和重击进行连击；立棍强调在蓄力重击时撑棍而起，以躲避地面攻击后再砸向敌人；戳棍则是以快速有力的蓄力重击戳向敌人为特点。",
            "systems_and_mechanics",
            [122, 123, 124, 125],
        ),
        (
            "黑风大王和黑熊精在形态与战斗表现上有什么不同？",
            "黑风大王是正常的人形BOSS，主要靠附魔长枪和长连招制造威胁，还能化成风进入无敌状态；黑熊精则是黑风大王的第二阶段，会从人形变成巨熊，血量变厚，攻击也变成大范围、前摇明显的招式。",
            "roles_and_bosses",
            [32, 35, 36],
        ),
        (
            "石先锋和石敢当有哪些相同点和不同点？",
            "两者都位于土地庙枕石坪左前方的同一区域，攻击套路也基本相近。不同之处在于石敢当是一个更灵活的石先锋，能够进行大范围的跳跃扑击；而且在收集六个佛眼珠后，还可以触发石敢当与石先锋的战斗，从而跳过石先锋的BOSS战。",
            "roles_and_bosses",
            [39, 40, 41],
        ),
        (
            "第一回和第二回在地点、帮助者和收获能力上分别是什么？",
            "第一回地点在黑风山，天命人得到土地公公的帮助，学会了定身术和聚形散气；第二回地点在黄风岭，天命人得到灵吉菩萨的帮助，学会了铜头铁臂和身外身法。",
            "story_flow",
            [51, 52, 53, 58, 59, 60],
        ),
        (
            "比较一下结局一和结局二的核心差别。",
            "两种结局都发生在击败大圣残躯之后，但走向不同。结局一天命人缺失大圣之“意”，最后心甘情愿戴上紧箍，再次沉睡于石卵之中；结局二则是天命人领悟了大圣之“意”，获得大圣意志的认可，拒绝戴上紧箍，六根再次重聚，齐天大圣重返世间。",
            "story_flow",
            [94, 95, 96, 97],
        ),
        (
            "普通变身和化身技在血条表现上有什么差别？",
            "普通变身成妖怪后，玩家会获得独立的血条；而装备精魄后发动的化身技虽然也会短暂变成对应妖怪并施展技能，但不会获得独立血条，受到伤害扣的仍是玩家自身的血量。",
            "systems_and_mechanics",
            [145, 147, 154, 155],
        ),
        (
            "定身法、聚形散气和铜头铁臂分别偏向什么用途？",
            "定身法主要是把对手定在原地，适合在对手无力之际施展；聚形散气偏向留下假身、散作清气遁走并伺机反击；铜头铁臂则是化作金石，借对手打在石上时将其震开后进行追击。",
            "systems_and_mechanics",
            [138, 140, 141, 142],
        ),
        (
            "出云棍、鳞棍·蟠龙和飞龙宝杖分别强化了哪类棍法？",
            "出云棍强化的是蓄力劈棍，伤害倍率加10%；鳞棍·蟠龙强化的是立棍，立棍招式伤害倍率加20%；飞龙宝杖则一定程度增加所有立棍招式的伤害，并能在三、四段蓄力立棍时引出天龙劈下落雷。",
            "items_and_equipment",
            [107, 108, 109, 110, 117, 118],
        ),
        (
            "再战系统里的复战和连战有什么区别？",
            "两者都属于通关一次游戏后可挑战强者的方式。复战更像单挑，并分为三个难度；连战则是车轮战，而且其中的强敌会使用与往昔不同的招式。",
            "systems_and_mechanics",
            [157, 158, 159, 160],
        ),
        (
            "从原文看，虎先锋和黄风大圣在战斗节奏上有什么区别？",
            "虎先锋虽然背着大剑，但大多数攻击依靠拳脚武术，招式变化多样，不适合用固定连招应对；黄风大圣则明确分为两个阶段，第一阶段更需要等待其打完连招再反击，第二阶段反而要求玩家更主动，否则容易被持续连招压制。",
            "roles_and_bosses",
            [37, 38, 42, 43],
        ),
        (
            "把第一回到第三回放在一起看，它们各自最后击败了谁，又拿到了哪一根？",
            "第一回最后在黑风洞击败黑熊精，获得“眼看喜”；第二回最后在黄风阵击败黄风大圣，获得“耳听怒”；第三回最后在小雷音寺击败黄眉，获得“鼻嗅爱”。",
            "story_flow",
            [56, 57, 63, 64, 71, 72],
        ),
        (
            "柳木棍和铜云棒的获得方式有什么不同？",
            "柳木棍是在天命人上路时由老猴子亲手打造的；铜云棒则是在购买豪华版后解锁，并且需要在土地庙的谢礼菜单中领取。",
            "items_and_equipment",
            [100, 101, 102],
        ),
        (
            "比较一下楮白枪和狼牙棒的核心效果。",
            "楮白枪会把枪术融入轻棍连招，重点是增加所有戳棍招式的伤害，并让轻击动作更好地使出劈棍法的识破；狼牙棒则是在识破对手攻击后，能够在短时间内不断获得棍势。",
            "items_and_equipment",
            [115, 116, 119, 120],
        ),
        (
            "从资料来看，金池长老和赤髯龙的触发方式有什么区别？",
            "两者都是隐藏BOSS，但触发流程不同。金池长老需要敲响三个分布在地图各处的大钟，传送到隐藏地图“隐·旧观音禅院”；赤髯龙则需要先在第二章击败沙大郎并取得龙鳞，再回到第一回瀑布处互动进入BOSS场地。",
            "roles_and_bosses",
            [33, 34],
        ),
        (
            "第二回和第三回在获得帮助或线索方面有什么不同？",
            "第二回里天命人得到的是灵吉菩萨的帮助，并借此学会铜头铁臂和身外身法；第三回则是与猪八戒相遇，还分别从袁守诚和弥勒佛处学会安身法和禁字法，并获得了关于浮屠塔的线索。",
            "story_flow",
            [59, 60, 66, 68, 69, 70],
        ),
    ]
    return [make_entry(i, o, "compare", c, r) for i, o, c, r in data]


def build_summary_entries():
    data = [
        ("请用一两句话概括《黑神话：悟空》的基本信息。", "《黑神话：悟空》由杭州游科互动科技有限公司开发，浙江出版集团数字传媒有限公司出版，是一款以《西游记》为背景设定的西游题材单机动作角色扮演游戏。玩家在游戏中扮演“天命人”，踏上探寻昔日传说真相的西游之路。", "basic_facts", [1, 2, 3, 6, 7]),
        ("简要总结序章讲了什么。", "序章借老猴子之口讲述孙悟空陨落之战：大圣与二郎显圣真君鏖战后被打落花果山，六根散于世间。天命人作为花果山的猴子猴孙之一，为了复活大圣而踏上寻找六根的道路。", "story_flow", [46, 47, 48, 49, 50]),
        ("请概括第一回“火照黑云”的主要经历。", "第一回发生在黑风山，天命人得到土地公公的帮助，学会定身术和聚形散气，打倒灵虚子、白衣秀士等强敌，超度金池长老的亡魂，最终在黑风洞击败黑熊精，并获得“眼看喜”。", "story_flow", [51, 52, 53, 54, 55, 56, 57]),
        ("用简短的话总结第二回“风起黄昏”的主线。", "第二回地点在黄风岭，天命人在灵吉菩萨帮助下学会铜头铁臂和身外身法，击败虎先锋和石先锋、探寻斯哈哩国往事，最后在黄风阵击败黄风大圣，取得“耳听怒”。", "story_flow", [58, 59, 60, 61, 62, 63, 64]),
        ("概括一下第三回“夜生白露”的关键内容。", "第三回发生在小西天，天命人逃离浮屠界后与猪八戒相遇，击败亢金星君、赤尻马猴以及众魔将，并从袁守诚和弥勒佛处分别学会安身法和禁字法，最后在小雷音寺击败黄眉，取得“鼻嗅爱”。", "story_flow", [65, 66, 67, 68, 69, 70, 71, 72]),
        ("第四回“曲度紫鸳”大致讲了什么？", "第四回地点在盘丝岭，天命人穿越盘丝洞、打倒蜘蛛精、解救猪八戒、找到紫云山入口并击败晦月魔君，最终在黄花观消灭百眼魔君，同时见证紫蛛儿油尽灯枯，猪八戒也与过去的感情作别。", "story_flow", [73, 74, 75, 76, 77]),
        ("请总结第五回“日落红尘”的主要剧情。", "第五回发生在火焰山，天命人先救下小狐狸，在璧水洞挖掘出红孩儿的身世，并见到牛魔王。随后小狐狸现出是红孩儿假扮的真相，大圣根器被夺，红孩儿化身夜叉王，最终被天命人击败并自我了断。", "story_flow", [78, 79, 80, 81, 82, 83, 84, 85, 86]),
        ("用一两句话概括第六回“未竟”的核心目标。", "第六回地点在花果山，天命人和猪八戒为孙悟空复活做最后准备，需要收集大圣散落的披挂、取回如意金箍棒，并一路突破天兵天将的封锁，最终在山顶石卵面对石猿与大圣残躯。", "story_flow", [87, 88, 89, 90, 91]),
        ("简要归纳结局一和结局二的分野。", "能否开启结局二，关键在于此前是否完成一系列隐藏支线并击败对应强敌。若未满足条件会进入结局一，天命人缺失大圣之“意”并再次沉睡；若满足条件则进入结局二，天命人领悟大圣之“意”，拒绝戴上紧箍，让六根重新聚合。", "story_flow", [92, 93, 94, 95, 96, 97]),
        ("请概括《黑神话：悟空》的战斗系统特点。", "游戏以棍棒为核心武器，提供劈棍、立棍、戳棍三种战斗方式。它没有格挡功能，主要依靠翻滚闪避来防御，攻击和闪避都会消耗气力，同时玩家还能通过升级、灵光点和法术系统不断强化自己的战斗能力。", "systems_and_mechanics", [121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133]),
        ("把主动法术系统浓缩总结一下。", "主动法术需要消耗法力释放，法力不足时可以在土地庙恢复。法术会随着剧情推进逐步解锁，并且每种法术都有自己的技能树，玩家可以消耗灵光点来提升法术效果。", "systems_and_mechanics", [134, 135, 136, 137]),
        ("请总结一下定身法、聚形散气、铜头铁臂和身外身法的共同作用。", "这四种能力都属于天命人在战斗中的重要法术或技巧，但用途各不相同：有的偏控制对手，有的偏闪避和诱敌，有的偏反震追击，还有的能召出多个毛猴协同作战，共同丰富了战斗策略。", "systems_and_mechanics", [138, 141, 142, 144]),
        ("概括一下妖怪变身机制。", "玩家可以在战斗中变身成妖怪，如狼妖或石妖，变身需要消耗神力，并且只有神力饱满时才能施展。变身后会获得独立血条，但神力会持续消耗，神力耗尽后又会恢复原形。", "systems_and_mechanics", [145, 146, 147, 148, 149]),
        ("用简短的话说明精魄系统是什么。", "第一回遇见老者后，游戏会解锁精魄系统。玩家击杀部分BOSS或精英怪后可用葫芦吸取精魄，装备后可获得属性提升或被动效果，还能发动化身技，并在土地庙消耗材料强化精魄。", "systems_and_mechanics", [150, 151, 152, 153, 154, 155, 156]),
        ("再战系统可以怎么概括？", "通关一次游戏后，玩家可以对已挑战过的强者再次挑战。系统支持复战和连战两种方式，复战有三个难度，连战中的强敌还会使用和过去不同的招式，此外玩家还能自行决定挑战难度和限制。", "systems_and_mechanics", [157, 158, 159, 160, 161]),
        ("请归纳游戏中的道具获取方式。", "游戏中的道具种类很多，包括兵器、头冠、衣甲、臂甲、腿甲、珍玩、精魄、葫芦等。它们通常需要通过探索、收集材料并炼制来获得，部分道具还需要在新的轮回中重复游玩才能收集完成。", "items_and_equipment", [98, 99]),
        ("把柳木棍到狼牙棒这一段兵器信息做个简要总结。", "这段兵器信息主要围绕武器的解锁条件和效果展开：有的跟随主线推进获得，有的需要击败特定BOSS、收集材料或完成隐藏流程后才能解锁，而且不同武器会分别强化轻棍、立棍、戳棍或识破等不同玩法。", "items_and_equipment", [100, 102, 103, 105, 107, 109, 111, 113, 115, 117, 119]),
        ("简要概括成就系统这一部分的特点。", "成就系统覆盖范围很广，既包括击败特定BOSS、完成支线、进入隐藏地图，也包括武器锻造、披挂升阶、收集种子、法术、葫芦、珍玩等收集与成长内容，几乎串联了整个游戏流程。", "achievements_and_lists", [162, 224]),
    ]
    return [make_entry(i, o, "summary", c, r) for i, o, c, r in data]


def build_step_entries():
    data = [
        ("金池长老这场隐藏战怎么触发？请按步骤说。", "先敲响分布在地图各处的三个大钟，然后会被传送到隐藏地图“隐·旧观音禅院”，在那里就能触发与金池长老的战斗。", "roles_and_bosses", [33]),
        ("如果要进入赤髯龙的BOSS房，大致流程是什么？", "先前往第二章击败沙大郎，再通过沙大郎敲碎战斗场地旁的墙获得龙鳞。之后回到第一回林外土地庙左上角的瀑布处，与瀑布互动，就能进入赤髯龙的BOSS场地。", "roles_and_bosses", [34]),
        ("想触发蝜蝂战，前面需要做哪些事？", "先传送到卧虎寺大门处，上楼梯往右前方走再次遇见一只猪，与其对话并交给他一个莲藕；再传送到第一次见面的地方开启与黄袍员外的战斗；击败黄袍员外后进入隐藏地图斯哈里国，继续往前便会触发与蝜蝂的战斗。", "roles_and_bosses", [44, 45]),
        ("请提取出解锁出云棍的关键步骤。", "先在“黄风岭-挟魂崖”找到6个佛目珠，再到“挟魂崖-枕石坪”石先锋所在区域使用佛目珠召唤并击败石敢当，获得材料“铁石心”后即可解锁出云棍的铸造。", "items_and_equipment", [107]),
        ("鳞棍·蟠龙要怎么解锁？请按原文顺序回答。", "先在BOSS沙大郎所在位置拿到飞龙鳞片，再前往第二回“挟魂崖-枕石坪”开启大门触发与小骊龙的BOSS战。击败小骊龙后，开启楼梯上方的宝箱获得材料“振雷骨”，之后即可解锁鳞棍·蟠龙的锻造。", "items_and_equipment", [109]),
        ("楮白枪的获取流程能梳理一下吗？", "先从四位魔将身上拿到4个道具，再回到土地庙“浮屠界-下层”，到初始牢房隔壁与小张太子对话交任务，获得“楮白枪头”，之后即可在土地庙或如意画轴中的寅虎处铸造楮白枪。", "items_and_equipment", [115]),
        ("飞龙宝杖的锻造前置步骤是什么？", "先到第三回“浮屠界-安身寺”，再到龟将背上的土地庙“龟岛”，面对土地庙往龟背右侧下层走，击败最下层的BOSS青背龙后，就能解锁飞龙宝杖的铸造。", "items_and_equipment", [117]),
        ("开启结局二大体要满足哪些连续条件？", "需要先在前面的关卡里开启隐藏支线，并击败金池长老、蝜蝂、翠笠武师、晦月魔君、避水金睛兽；之后前往浮屠塔见到弥勒佛，在其帮助下进入隐藏地图梅山；最后击败二郎显圣真君，并打倒四大天王以及二郎神的法相，这样才会达成结局二的开启条件。", "story_flow", [92]),
        ("按资料顺序说说第六回为了复活孙悟空都做了什么准备。", "先收集孙悟空散落的披挂，包括凤翅紫金冠、锁子黄金甲、藕丝步云履、点翠飞龙釬；接着前往水帘洞拿起如意金箍棒；然后一路突破天兵天将的封锁，进入山顶石卵，准备面对石猿与大圣残躯。", "story_flow", [88, 89, 90, 91]),
        ("如果想利用石敢当跳过石先锋战，需要满足什么前提？", "前提是先收集六个佛眼珠。满足这个条件后，就能激活石敢当与石先锋的战斗，而最终胜者会是石敢当，从而跳过石先锋的BOSS战。", "roles_and_bosses", [39, 40, 41]),
        ("精魄系统是怎么解锁并继续使用下去的？请按流程概括。", "第一回遇见老者后，游戏会解锁精魄系统。之后击杀部分BOSS或精英怪可用葫芦吸取精魄，即使在捡起前死亡也不会丢失，还能在土地庙重拾；装备精魄后可获得属性或被动效果，并发动化身技，最后也能在土地庙消耗材料强化精魄。", "systems_and_mechanics", [150, 151, 152, 153, 154, 156]),
        ("再战系统开放后，玩家可以如何设置挑战？", "通关一次游戏后，再战系统就会开放。玩家可以选择复战或连战，其中复战分为三个难度，连战中的强敌会使用不同于往昔的招式，而且玩家还可以自行决定挑战难度和限制。", "systems_and_mechanics", [157, 158, 159, 160, 161]),
        ("原文里天命人为了复活大圣是怎么起步的？", "序章中，天命人先在花果山聆听老猴子讲述大圣陨落之战，在得知六根散于世间后，作为猴子猴孙中的一员，毅然踏上寻找六根的路途，以复活大圣。", "story_flow", [46, 47, 48, 49, 50]),
        ("请提取第一回到第三回中学会能力的顺序。", "第一回中，天命人学会了定身术和聚形散气；第二回中学会了铜头铁臂和身外身法；第三回中又从袁守诚处学会安身法，从弥勒佛处学会禁字法。", "story_flow", [53, 60, 68, 69]),
        ("如果只看给定资料，铜云棒的领取路径是什么？", "铜云棒需要在购买豪华版后解锁，随后前往土地庙的谢礼菜单中领取。", "items_and_equipment", [102]),
    ]
    return [make_entry(i, o, "step_extraction", c, r) for i, o, c, r in data]


def build_knowledge_units(base_entries):
    units = []
    groups = {
        "basic_facts": "基础事实",
        "roles_and_bosses": "角色与BOSS",
        "story_flow": "剧情流程",
        "items_and_equipment": "道具与装备",
        "systems_and_mechanics": "系统机制",
        "achievements_and_lists": "成就与列表知识",
    }
    task_support = {
        "basic_facts": ["qa", "qa_variant", "judgment", "summary"],
        "roles_and_bosses": ["qa", "qa_variant", "judgment", "compare", "step_extraction"],
        "story_flow": ["qa", "qa_variant", "judgment", "compare", "summary", "step_extraction"],
        "items_and_equipment": ["qa", "qa_variant", "judgment", "compare", "summary", "step_extraction"],
        "systems_and_mechanics": ["qa", "qa_variant", "judgment", "compare", "summary", "step_extraction"],
        "achievements_and_lists": ["qa", "judgment", "summary"],
    }
    for category, title in groups.items():
        refs = [e["source_id"] for e in base_entries if e["category"] == category]
        units.append(
            {
                "category": category,
                "title": title,
                "source_refs": refs,
                "supported_tasks": task_support[category],
            }
        )
    return units


def dedupe_entries(entries):
    seen = set()
    deduped = []
    for entry in entries:
        key = (entry["instruction"], entry["output"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def max_consecutive(entries, field):
    if not entries:
        return 0
    best = 1
    current = 1
    last = entries[0][field]
    for entry in entries[1:]:
        if entry[field] == last:
            current += 1
            best = max(best, current)
        else:
            current = 1
            last = entry[field]
    return best


def stagger_entries(entries):
    buckets = {}
    for entry in entries:
        buckets.setdefault(entry["task"], []).append(entry)
    for bucket in buckets.values():
        random.shuffle(bucket)

    task_order = ["qa", "qa_variant", "judgment", "compare", "summary", "step_extraction"]
    arranged = []
    while any(buckets.values()):
        progress = False
        for task in task_order:
            bucket = buckets.get(task, [])
            if not bucket:
                continue
            candidate_idx = 0
            if arranged:
                for idx, candidate in enumerate(bucket):
                    same_task = arranged[-1]["task"] == candidate["task"]
                    same_category = arranged[-1]["category"] == candidate["category"]
                    if not (same_task and same_category):
                        candidate_idx = idx
                        break
            arranged.append(bucket.pop(candidate_idx))
            progress = True
        if not progress:
            break
    return arranged


def write_jsonl(entries, path):
    with path.open("w", encoding="utf-8") as f:
        for entry in entries:
            row = {
                "instruction": entry["instruction"],
                "output": entry["output"],
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_report(entries, knowledge_units):
    task_counter = Counter(entry["task"] for entry in entries)
    category_counter = Counter(entry["category"] for entry in entries)
    length_counter = Counter(entry["answer_length"] for entry in entries)
    prefix_counter = Counter(entry["instruction"][:6] for entry in entries)
    top_prefixes = prefix_counter.most_common(10)
    return {
        "total_samples": len(entries),
        "task_distribution": dict(task_counter),
        "category_distribution": dict(category_counter),
        "answer_length_distribution": dict(length_counter),
        "knowledge_units_count": len(knowledge_units),
        "quality_checks": {
            "max_consecutive_same_task": max_consecutive(entries, "task"),
            "max_consecutive_same_category": max_consecutive(entries, "category"),
            "unique_instruction_prefixes": len(prefix_counter),
            "top_instruction_prefixes": top_prefixes,
        },
        "notes": [
            "所有样本答案均限制为给定原文可支持的内容。",
            "增强集混合了问答、判断、对比、总结和步骤提取任务。",
            "最终 JSONL 仅保留 instruction 和 output 两个字段，便于直接用于 SFT。",
        ],
    }


def build_workflow_markdown(report):
    return f"""# 黑神话增强集工作流

## 产物
- `blackwukong_augmented_20260429.jsonl`
- `blackwukong_knowledge_units_20260429.json`
- `blackwukong_augmented_20260429_report.json`

## 本次数据概况
- 总样本数：{report["total_samples"]}
- 任务分布：{json.dumps(report["task_distribution"], ensure_ascii=False)}
- 类别分布：{json.dumps(report["category_distribution"], ensure_ascii=False)}
- 长度分布：{json.dumps(report["answer_length_distribution"], ensure_ascii=False)}

## 生成流程
1. 读取基础问答集 `blackwukong_base_20260429.jsonl`。
2. 按行号把样本拆分为基础事实、角色与BOSS、剧情流程、道具与装备、系统机制、成就与列表知识六类知识单元。
3. 在基础问答之上生成五类增强任务：问答改写、判断、对比、总结、步骤提取。
4. 对生成结果执行去重，并按任务和类别交错打散，避免连续出现过多同类样本。
5. 输出最终 JSONL，并同步产出知识单元清单与质检报告。

## 下一版扩展建议
1. 优先补充 `compare`、`summary`、`step_extraction` 三类任务，把它们的占比继续提高。
2. 对成就系统增加更多“集合判断”和“范围总结”样本，而不是继续堆单点问答。
3. 把章节剧情拆成更细的事件链，增加跨章节对比和条件判断样本。
4. 如果要继续扩容到 600 条以上，优先新增原文支持的长答总结，而不是重复做浅层同义改写。

## 重新生成
```bash
python AI/llm/code/qwen/data/build_blackwukong_augmented_20260429.py
```
"""


def main():
    base_entries = load_base_entries()
    selected_base_entries = select_base_training_entries(base_entries)
    variant_facts = build_variant_facts(base_entries)
    judgments = build_positive_judgments(base_entries) + build_negative_judgments()
    compares = build_compare_entries()
    summaries = build_summary_entries()
    steps = build_step_entries()

    final_entries = dedupe_entries(selected_base_entries + variant_facts + judgments + compares + summaries + steps)
    final_entries = stagger_entries(final_entries)
    knowledge_units = build_knowledge_units(base_entries)
    report = build_report(final_entries, knowledge_units)

    write_jsonl(final_entries, OUT_PATH)
    KNOWLEDGE_UNITS_PATH.write_text(json.dumps(knowledge_units, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    WORKFLOW_PATH.write_text(build_workflow_markdown(report), encoding="utf-8")

    print(f"generated_samples={len(final_entries)}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
