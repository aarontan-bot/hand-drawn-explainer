# vendor 说明

来源 https://github.com/yang0/handraw-style（MIT，作者 @yang02010），浅克隆 master@6daf50f，2026-09-18 快照，已去掉 .git。
只用它的 `handdraw-style-prompter/references/styles.json`（268 种风格：编号 / 分组 / 参考作者 / 风格名 / 特征）、`images/individual/` 编号参考图与 `handdraw-style-prompter/gallery/index.html` 画廊。
更新：重新浅克隆覆盖本目录，保留本文件。

**图片不进本仓库**：`images/`（334 张 webp，约 23 MB）由 `fetch-images.sh` 按需从上游拉取，
版本锁在上面记的快照——脚本里写的是完整 40 位 SHA `6daf50f59693b58e3127598d7db88031498880de`，
因为按短 SHA fetch 服务端认不出来，会静默退到默认分支的最新版（实测上游已更新到 340 张，
编号与本目录的 styles.json 不一定对得上）。拉完脚本会校验编号覆盖情况，对不上会警告。
