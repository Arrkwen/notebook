# 黑神话增强集工作流

## 产物
- `blackwukong_augmented_20260429.jsonl`
- `blackwukong_knowledge_units_20260429.json`
- `blackwukong_augmented_20260429_report.json`

## 本次数据概况
- 总样本数：403
- 任务分布：{"qa": 170, "qa_variant": 120, "judgment": 65, "compare": 15, "summary": 18, "step_extraction": 15}
- 类别分布：{"achievements_and_lists": 27, "story_flow": 121, "systems_and_mechanics": 55, "roles_and_bosses": 71, "items_and_equipment": 59, "basic_facts": 70}
- 长度分布：{"short": 114, "medium": 232, "long": 57}

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
