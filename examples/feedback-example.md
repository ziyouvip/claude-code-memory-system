---
name: feedback-commit-timing
description: 改完代码不主动提交
metadata:
  type: feedback
---

改完代码后不要自动 commit 或 push。等用户在本地验证功能正常后，再由用户确认提交。

**Why:** 自动提交会打断用户的验证节奏，且一旦 push 到远端就需要额外操作回滚。

**How to apply:** 完成代码修改后，明确告知用户改动内容，等待其确认再执行 git 操作。
