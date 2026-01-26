---
name: codebase-fast-understanding-for-maintenance
description: 快速建立对大型代码库的整体认知，面向接手维护/排障，不逐行阅读源码。适用于“我快速了解这个项目/代码库/原型/实现逻辑/怎么实现的”等场景。
---

# Codebase Fast Understanding for Maintenance

## Goal

在不逐行、逐函数深入实现细节的前提下，快速建立对代码库的整体认知，重点理解系统架构、模块职责、核心执行流程，以支持维护与排障。

## Required Inputs (ask if missing)

- CODEBASE_SIZE: 代码库规模（如：>50k 行 / 大型）
- LANGUAGE_STACK: 主要编程语言或技术栈
- PROJECT_TYPE: 项目类型（系统组件 / 后台服务 / SDK / 工具链等）
- ENTRY_POINT: 程序主入口（如 main / 启动脚本 / 服务入口）
- BUILD_OR_RUN: 构建或启动方式（make / cmake / python -m / systemd 等）
- CORE_PATHS (optional): 核心模块或包所在路径
- TIME_LIMIT (default 30): 期望在多少分钟内完成整体理解
- CORE_ITEMS_COUNT (default 3-5): 需要优先理解的核心文件或模块数量

If the user doesn’t provide optional fields, proceed with reasonable assumptions and state them explicitly.

## Workflow

1) Give a system architecture overview: layers/subsystems and responsibilities.
2) Identify core modules/packages and explain:
   - 模块职责
   - 主要输入与输出
   - 模块之间的依赖关系
3) Describe the core execution flow:
   入口 → 初始化阶段 → 关键逻辑路径。
4) 从维护视角给出导航建议：
   - 首次应重点阅读的文件或模块
   - 常见排障会涉及的路径
   - 修改风险较高的关键位置

## Constraints

- 不逐行讲解源码。
- 不展开函数或方法的内部实现。
- 不假设代码中未体现的业务背景。
- 不泛讲语言或架构通用概念。
- 不对代码质量或设计优劣做评价。

## Output Format (Markdown)

- 总体架构概览
- 核心模块与职责
- 核心执行流程
- 面向维护的导航建议

Also explicitly call out CORE_ITEMS_COUNT 个必须优先理解的核心文件或模块。

## Success Criteria

- 维护人员在 TIME_LIMIT 分钟内能够：
  - 说明系统整体功能
  - 描述主要模块的职责划分
  - 复述核心执行流程
- 明确指出 CORE_ITEMS_COUNT 个必须优先理解的核心文件或模块
