# Shizuku Shell

通过 Shizuku 以 shell 身份（uid 2000）执行命令。

改动：

- 新增 `ShizukuShellService`（复用工程里已有的 dev.rikka.shizuku 依赖）
- 新增 `shizuku_shell` 工具
- `SystemToolsSetting` 新增 `shizukuShellEnabled`
- 系统工具页新增「Shizuku 命令行」卡片

开关位置：设置 → 系统工具 → 最底部
