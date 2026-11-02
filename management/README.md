# Agent Governance V0.2

项目 ID：0c68bf5a-2104-498a-9532-7a2f6f2384f3

此目录是从 Git 公共目录中的治理事件账本生成的阅读视图。正式操作使用项目内 CLI。
自然语言操作归档、重置和决策前，先读 .pi/governance/OPERATOR-GUIDE.md；日常使用无需查看治理源码。
management/policies/subagents.json 是可编辑的项目路由策略；修改后先检查，再明确批准摘要。其他状态视图仍从账本生成。

```sh
node .pi/governance/cli.ts state show
node .pi/governance/cli.ts run inspect R-实际ID
node .pi/governance/cli.ts run reconcile R-实际ID
node .pi/governance/cli.ts policy show
node .pi/governance/cli.ts policy approve
node .pi/governance/cli.ts audit delegations T-实际ID
node .pi/governance/cli.ts audit run R-实际ID
node .pi/governance/cli.ts views render
node .pi/governance/cli.ts backup export /safe/location/events.jsonl
```

查看 NOW.md 了解进度，INBOX.md 处理待审批事项。不要直接编辑生成视图作为授权记录。
