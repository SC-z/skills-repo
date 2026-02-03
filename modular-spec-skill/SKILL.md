---
name: modular-spec-skill
description: >
  模块级 Spec 生成主 Skill。
  基于统一架构语义，在不同使用场景（A/B/C）下调度子 Skill，
  输出“总-分”结构的模块设计 Spec，并将结果持久化保存，
  用于团队级思想对齐与长期演进。
---

# 主 Skill：模块级 Spec 生成（分发与约束层）

## 一、Skill 定位

本 Skill 是**唯一入口 Skill**，负责：

- 统一解析整体架构语义
- 判断使用场景（A/B/C）
- 调度对应子 Skill
- 生成并组织“总-分”结构的 Spec 输出
- 约束输出结构与最小信息集

⚠️ 本 Skill **不直接生成具体分析内容**，  
仅负责 **调度、结构组织、约束与一致性保证**。

---

## 二、目录结构约定

```text
<skill-root>/
├─ SKILL.md
├─ skills/
│   ├─ architecture-parser.md
│   ├─ design-motivation.md
│   ├─ core-flow.md
│   ├─ boundary-analysis.md
│   └─ evolution-risk.md
└─ templates/
    ├─ global-spec-template.md
    └─ module-spec-template.md
```

---

## 三、输入定义

### 必填输入
- **整体架构描述**  
  系统级架构说明、设计原则、全局约束

- **目标模块范围**  
  模块列表 / 包结构 / 目录结构（可多模块）

### 可选输入
- **使用场景标识**：`A | B | C`
  - A：新模块沉淀
  - B：Code Review / 合并前
  - C：接手 / 重构  
  （默认：B）

- **模块源码路径**

---

## 四、使用场景定义

- **场景 A｜新模块沉淀**
  - 强调：设计动机、设计取舍、长期演进

- **场景 B｜Code Review / 合并前**
  - 强调：核心流程、实现合理性、潜在风险

- **场景 C｜接手 / 重构**
  - 强调：模块边界、职责拆分、重构风险

---

## 五、执行模型

### 全局前置阶段（只执行一次）

```text
run(skills/architecture-parser)
```

输出：
- 统一架构语义上下文
- 模块划分与依赖关系视图

该输出将作为：
- **全局 Spec 的核心输入**
- **所有模块级 Spec 的共同前提**

---

### 全局 Spec 生成（总）

基于 `architecture-parser` 的输出：

- 生成 **全局架构分析 Spec**
- 描述：
  - 系统整体结构
  - 模块划分原则
  - 模块之间的功能协作关系
  - 关键依赖与控制流方向

输出文件：
```text
spec-docs/global-spec.md
```

⚠️ 全局 Spec **只做概览与关联说明**，  
不展开模块内部细节。

---

### 模块级 Spec 生成（分）

对每一个目标模块，执行以下流程：

#### 场景分发调度

```text
if scene == "A":
    run(skills/design-motivation)
    run(skills/evolution-risk)

elif scene == "B":
    run(skills/core-flow)
    run(skills/evolution-risk)

elif scene == "C":
    run(skills/boundary-analysis)
    run(skills/core-flow)
    run(skills/evolution-risk)
```

设计原则：
- 子 Skill **只关注单一分析维度**
- 所有模块：
  - 使用同一 Spec 模板
  - 在不同场景下分析深度不同

---

## 六、输出结果（新增，关键）

###  输出结构（总-分）

- **全局 Spec（总）**
  - 描述系统级结构与模块协作关系
- **模块 Spec（分）**
  - 每个模块一份独立文档
  - 不相互混写

###  持久化规则

- 全局 Spec：
  ```text
  spec-docs/global-spec.md
  ```

- 模块 Spec：
  ```text
  spec-docs/modules/<module-name>.md
  ```

###  输出保证

- 每个模块 **必然生成一份 Spec**
- Spec 文档：
  - 可直接提交到仓库
  - 可用于 Review / 设计讨论 / 交接

---

## 七、输出约束

### 输出结果与持久化规则

- 本 Skill 不在自身目录中生成任何输出
- 所有分析结果必须写入「被分析项目的代码目录」
- 输出目录默认约定为：

<target-project-root>/spec-docs/

### 输出结构（语义结构，而非 Skill 目录）
```text
spec-docs/
├─ global-spec.md        # 系统级全局分析 Spec
└─ modules/
    ├─ <module-name>.md  # 单模块 Spec
    └─ ...
```

### 模块级 Spec 最小字段集

无论场景，必须包含：
- 模块定位与职责
- 核心功能说明
- 关键设计或流程
- 已知限制 / 风险

---

## 八、强约束与禁止事项

- ❌ 禁止跨模块混写 Spec
- ❌ 禁止模块 Spec 承担系统级说明
- ❌ 禁止子 Skill 直接生成文件结构
- ❌ 禁止在 Spec 中引入未解析的架构前提

---

## 九、Skill 目标总结

本 Skill 的最终目标是：

> **形成一个“可沉淀、可演进、可复用”的  
> 系统设计知识资产，而不是一次性分析输出。**
```

