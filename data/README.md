# 数据目录

```text
data/
├── raw/
│   ├── screenagent/ScreenAgent/{train,test}/...
│   ├── webarena/config_files/*.json
│   └── mind2web/data/{train,test_task,test_website,test_domain}/*.json
└── processed/
    ├── screenagent.jsonl
    ├── webarena.jsonl
    └── mind2web.jsonl
```

`raw` 和 `processed` 已加入 `.gitignore`。原始数据需要用户按
`docs/phase2-download-guide.md` 下载；处理后的 JSONL 由项目脚本生成。
