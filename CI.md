# orangechat CI 备注

## Release Build (.github/workflows/release.yml)

2026-11-08 打通，跑通一次大约 9~12 分钟。

关键点：
1. 不需要签名密钥 secret。CI 里用 keytool 现场生成 `app/release.keystore`，
   同时写 `local.properties`（storeFile=release.keystore / storePassword / keyAlias / keyPassword），
   Gradle 直接读取。口令统一 orangechat2026。
2. 仓库 Settings → Actions → General → Workflow permissions 必须选
   **Read and write permissions**，否则 `gh release create` 会报
   `HTTP 403: Resource not accessible by integration`。
   workflow 里也要写 `permissions: contents: write`，两边缺一不可。
3. 失败时 job 会自动把 build.log 摘要推到仓库根目录 `ci-last-error.log`，
   直接 raw 拉取就能看错误，不用翻网页日志。
4. 触发：workflow_dispatch，或推 `v*` tag。
5. 产物：app-arm64-v8a / app-universal / app-x86_64 三个 release apk。
