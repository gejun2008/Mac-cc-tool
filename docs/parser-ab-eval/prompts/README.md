# Prompt 日志

给 Copilot 的每一条指令原样归档,用于复现和追责。

命名:`NNN-<slug>.md`,序号连续,不补不跳。

每个文件开头带 front matter:

```
---
date: YYYY-MM-DD
stage: STAGE N
target: 受影响的文件
result: 见 commit <sha>
---
```

正文是原话,不要事后修饰。
