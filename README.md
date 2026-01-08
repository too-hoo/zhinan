# 如何在线上终端运行？

1、提交代码：在 Codespaces 里把这两个新文件 Commit & Push 到 GitHub。

2、等待部署：Zeabur 会自动拉取新代码并部署。

3、进入终端：打开 Zeabur 控制台的 Terminal。

4、执行指令：

```bash
# 赋予执行权限
chmod +x init_online.sh
./init_online.sh
```
5、配置环境变量：
OSS_ACCESS_KEY_ID=你的
OSS_ACCESS_KEY_SECRET=你的
GEMINI_API_KEY=你的

