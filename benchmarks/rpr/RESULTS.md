# RPR partition benchmark：演进、结果与最终选择

本文整理 `benchmarks/rpr/results/` 中已有实验，说明 RPR partition 部分经历了
哪些改动、各改动解决了什么问题，以及当前生产 benchmark 为什么选择现在的
配置。结论基于截至 2026-11-06 留存的结果文件。

原始运行目录已在完成本文汇总后清理，以避免长期保留约 2.7 GB 的 root mappings、
roots 和运行日志。下文中的 `results/...` 名称是历史实验标识；长期保留
的是可复现 runner、dataset/configuration contract、compact baseline 和本文记录。

这里的历史结果并不全都可以直接横向比较：2026-10-17 的早期实验使用旧的
`20261017-partition-optimization-baseline` 输入，2026-10-21 的最终实验使用
schema-4 生产输入。本文只在输入、参数和输出语义一致的实验组内计算性能差异；
跨组数据只用于说明方案演进。

## 最终结论

当前生产选择是：

- 求解器：`rpr`，即 Relax-Project-Refine（RPR），而不是早期的
  variable-neighborhood 区域替换求解器。
- 可行域：directed-admissible rooted partition。
- 目标：精确 `J_lambda`，`recall_weight = 1/2`，使用整数交叉乘法比较，避免
  浮点舍入改变决策。
- 初始化：`asc`。
- 搜索参数：`max_epochs = 5`、`min_delta = 0.01`。
- 运行参数：48 OpenMP threads、release profile、LTO。
- 工程实现：直接信任已验证的 schema-4 CSR；在 CSR 中缓存紧凑 node
  length；summarized admissibility coverage 按 root 邻接扫描；释放不再需要的
  canonical buffer；local-move 按 degree work 做确定性连续分区；保留逐节点
  primary root mapping。
- 没有采用：sparse counters、12/24 线程替代 48 线程、实验性的 cost-plan
  组合，以及旧 variable-neighborhood 求解器。

最终基线来自 `results/20261106-local-move-production-repeat/benchmark.json`：

| 项目 | 结果 |
|---|---:|
| unique nodes | 5,216,490 |
| relation edges (`m`) | 181,664,804 |
| true-positive edges (`T`) | 52,505,486 |
| predicted pairs (`P`) | 68,039,827 |
| precision | 0.771687529 |
| recall | 0.289023987 |
| F1 | 0.420540747 |
| roots | 1,296,308 |
| root identity | `405b31f5f3e12f32` |
| admissibility coverage memberships | 13,130,585 |
| wall time | 17.483 s |
| peak RSS | 5,026,648,064 bytes (4.68 GiB) |
| termination | `min_delta_reached` |

这不是“代表元数量最少”的选择，而是在当前目标函数和三个初始化候选中
`J_{1/2}` / F1 最好的选择。

## Benchmark 合同

最终标准 benchmark 只计时 partition；createdb 和 createtopo 不在计时范围内。
固定输入和配置分别记录在：

- `datasets/current.json`：schema-4 node universe/reference graph 身份；
- `configs/production.json`：`1/2`、5 epochs、`0.01`、`asc`、48 threads；
- `baselines/production-schema4.json`：正确性和性能基线。

正确性 gate 不只比较 F1，还精确比较输入身份、参数、`T/P/m`、代表元身份和
数量、admissibility coverage membership 数量、终止原因以及稳定输出文件的 SHA-256。性能 gate
允许 wall time 增长 `max(3%, 2 s)`，RSS 增长 `max(5%, 256 MiB)`。因此，小于
该范围的单次时间变化不能单独视为确定的优化或退化。

## 1. 早期方案：先降低内存，但仍无法完成

2026-10-16 至 2026-10-17 的第一批实现围绕 CSR、quotient、region queue 和
singleton/lazy materialization 做了多轮尝试。它们确实逐步降低了内存，但在
180 秒限制内仍全部超时。

| 代表性实验 | wall time | peak RSS | 结论 |
|---|---:|---:|---|
| `current-baseline` | 180 s timeout | 14.57 GiB | 旧基线不可用 |
| `bounded-region-queue` | 180 s timeout | 9.75 GiB | 内存下降，仍超时 |
| `parallel-lazy-quotient` | 180 s timeout | 7.60 GiB | 继续下降，仍超时 |
| `new-solver-repaired-f1` | 180 s timeout | 3.30 GiB | 内存已可控，但计算仍未完成 |

这一阶段的价值主要是排除了“只优化旧 quotient/region 数据结构就足够”的
判断：瓶颈已经不只是内存布局，而是搜索策略本身。

`new-solver-static-gate` 目录没有留下完整报告，不能作为性能或正确性证据。

## 2. Variable-neighborhood：修复了精确比例，但方案本身被淘汰

随后实现了 `admissible_rooted_variable_neighborhood`，用区域级 star-closed
replacement 扩展解。它能在约 50 秒内结束，但得到的解几乎是全 singleton：

| 实验 | solver | wall time | peak RSS | `T/P` | roots | F1 |
|---|---|---:|---:|---:|---:|---:|
| `wave2-production` | v4 | 51.015 s | 18.44 GiB | 10 / 10 | 5,216,486 | 错误记录为 0 |
| `wave2-exact-ratio` | v5 | 50.031 s | 18.45 GiB | 10 / 10 | 5,216,486 | `10/90832407` |

v4 的 recall/F1 被整数舍入为 0；v5 改为精确有理数后，数值记录恢复正确。
但是正确的 F1 也只有约 `1.10e-7`，且 RSS 接近 20 GB。两轮 wave 只接受了
两个 replacement，区域搜索没有从 canonical singleton basin 中有效走出来。

因此最终判断是：**精确比例修复必须保留，但 variable-neighborhood 搜索策略
不能作为生产求解器。**

## 3. 改用 RPR：算法层面的决定性变化

`rpr` 通过 Relax-Project-Refine 周期性解除 root 结构限制，再投影
回合法 star，并进行 legal refinement。schema-4 上最初的 `desc` 两次运行得到
完全相同的 `T/P/F1`：

| run | wall time | peak RSS (GB, 10^9 B) | `T` | `P` | F1 |
|---|---:|---:|---:|---:|---:|
| `current-schema4-partition-run1` | 90.033 s | 4.817 GB | 52,091,435 | 70,867,481 | 0.412552676 |
| `current-schema4-partition-run2` | 88.895 s | 4.783 GB | 52,091,435 | 70,867,481 | 0.412552676 |

与 variable-neighborhood 的 `T=10` 相比，这不是微调，而是从退化解切换到
有效生产解；同时内存由约 19.8 GB 降到约 4.8 GB。此后所有生产优化都建立在
RPR 上，并要求 `T/P/F1` 精确不变。

## 4. RPR 工程优化链

下面各项使用相同的 `desc` 初始化和相同输出语义。最初两次 RPR 运行的平均
时间为 89.464 秒，平均 RSS 约 4.80 GB。

| 阶段 | 主要改动 | wall time | peak RSS (GB, 10^9 B) | 输出 | 决策 |
|---|---|---:|---:|---|---|
| initial RPR | schema-4 初始实现，两次平均 | 89.464 s | 4.80 GB | 基准 `T/P/F1` | 起点 |
| opt1 | trusted CSR fast path | 62.382 s | 4.766 GB | 精确不变 | 保留 |
| opt2 | sparse counters | 70.874 s | 4.761 GB | 精确不变 | 淘汰 |
| opt3 | summarized admissibility coverage | 63.454 s | 4.467 GB | 精确不变 | 保留 |
| opt4 | 提前释放 canonical buffer | 62.214 s | 3.509 GB | 精确不变 | 保留 |
| opt5 | 12-thread probe | 61.535 s | 3.535 GB | 精确不变 | 仅探针 |
| opt5 | 24-thread probe | 61.297 s | 3.521 GB | 精确不变 | 仅探针 |
| opt6 | release + LTO，run 1 | 60.514 s | 3.502 GB | 精确不变 | 保留 |
| opt6 | release + LTO，run 2 | 60.159 s | 3.517 GB | 精确不变 | 保留 |

具体判断如下：

1. **Trusted CSR 是最大的纯工程加速。** 输入 artifact 已经过 schema、identity、
   checksum 和结构验证后，partition 热路径不再重复构建/验证等价结构，时间从约
   89.5 秒降到 62.4 秒，输出未改变。
2. **Sparse counters 不值得保留。** RSS 只减少约 4 MB，时间却从 62.4 秒增加
   到 70.9 秒。
3. **Summarized admissibility coverage 是正确的内存边界。** 它不物化每个节点的全部重叠 admissibility coverage
   memberships，因此直接调用 `admissibility coverage.memberships(node)` 会抛出异常；但这不等于
   丢失 node-to-root 结果。primary root mapping 仍完整存在，并输出为
   `root_of.tsv`，每个 node 都有唯一 root。
4. **释放 canonical buffer 是最大内存优化。** 相比 opt3，RSS 从 4.467 GB
   降到 3.509 GB，时间没有退化。
5. **12/24 线程没有足够证据替代 48 线程。** 它们相对 48-thread opt4 只快
   0.7--0.9 秒，小于 benchmark 的 2 秒容差，而且生产合同仍固定 48 threads。
6. **LTO 有小幅且可重复的收益。** 两次结果约 60.2--60.5 秒，RSS 与 opt4
   基本相同，因此进入最终工程实现。

从 initial RPR 到 opt6，`desc` 路线的 wall time 约降低 32.6%，RSS 约降低
26.8%，且 `T/P/F1` 精确不变。

## 5. Cost-plan 组合：测过，但没有进入最终基线

随后分别在 solver、shards 和 admissibility coverage 路径试验 cost-aware work planning：

| 组合 | wall time | peak RSS (GB, 10^9 B) |
|---|---:|---:|
| solver only | 59.917 s | 3.529 GB |
| admissibility coverage only | 61.581 s | 3.503 GB |
| solver + shards | 60.501 s | 3.530 GB |
| shards + admissibility coverage | 61.473 s | 3.527 GB |
| solver + shards + admissibility coverage, run 1 | 59.555 s | 3.548 GB |
| solver + shards + admissibility coverage, run 2 | 59.113 s | 3.575 GB |

所有组合的 `T/P/F1` 都与 opt6 完全一致。全组合平均约 59.33 秒，比 opt6 平均
约快 1.00 秒，但这个差值低于性能 gate 的 2 秒绝对容差，同时 RSS 略高。

最终三个 initialization 标准运行的 native build SHA-256 与 opt6 相同
（`249d8276...`），并非任一 cost-plan 构建；当前 partition 源码也没有保留这组
work-plan 路径。因此应把它们记录为**有希望但证据不足、最终未采用**的实验，
不能把 59.113 秒当作当前生产实现的基线。

## 6. Initialization 选择

在相同 schema-4 输入、`recall_weight=1/2`、5 epochs、`min_delta=0.01`、
48 threads 和同一个 opt6 native build 下，对三个初始化做了直接比较：

| initialization | wall time | peak RSS (GB, 10^9 B) | precision | recall | F1 | roots | admissibility coverage memberships |
|---|---:|---:|---:|---:|---:|---:|---:|
| `asc` | 73.768 s | 3.853 GB | 0.771315706 | 0.288951513 | **0.420408811** | 1,296,041 | 13,089,471 |
| `desc` | **69.731 s** | **3.499 GB** | 0.735054136 | 0.286744784 | 0.412552676 | **1,293,599** | 13,245,806 |
| `local` | 74.069 s | 3.694 GB | 0.743531463 | 0.288191911 | 0.415382182 | 1,296,770 | 13,139,234 |

`desc` 更快、RSS 更低、代表元少 2,442 个，但当前 objective 并不直接最小化
代表元数量。`asc` 的 F1 比 `desc` 高约 1.90%，比 `local` 高约 1.21%，因此
最终选择 `asc`。这也解释了为什么不能把 cost-plan/opt6 的约 60 秒 `desc`
结果与最终 73.768 秒 `asc` 基线直接当作同一个解的性能回归。

## 7. Recall-weight 扫描

使用 `desc` 初始化的参数扫描展示了 precision/recall 取舍：

| `recall_weight` | precision | recall | F1 | wall time | peak RSS (GB, 10^9 B) |
|---:|---:|---:|---:|---:|---:|
| 0（旧 `single_edge` seed） | 1.000000000 | 0.000000006 | 0.000000011 | 67.391 s | 19.002 GB |
| 0（正常 `desc`） | 0.999999940 | 0.183294674 | 0.309803933 | 102.867 s | 5.142 GB |
| 0.001 | 0.999993801 | 0.183800385 | 0.310525678 | 100.105 s | 5.175 GB |
| 0.1 | 0.953964497 | 0.237243016 | 0.379986546 | 96.271 s | 5.001 GB |
| 0.5 | 0.735054136 | 0.286744784 | **0.412552676** | 69.731 s | 3.499 GB |
| 0.9 | 0.513200573 | 0.289845242 | 0.370461414 | 76.593 s | 4.858 GB |
| 1 | 0.472172371 | 0.287243147 | 0.357191220 | 81.782 s | 4.776 GB |

第一条 `recall_weight=0` 结果需要单独解释。此时目标只看 precision；
`single_edge` seed 得到 `T=P=1`，precision 恰好为 1，因此从数学上已经达到
纯 precision 目标的上界，求解器以 `no_strict_improvement` 终止。它不是 F1
计算错误，而是目标在 lambda=0 时允许的退化最优解，对实际聚类没有意义。

后续 `recall-weight-0-normal-desc-no-single-edge` 改回正常 `desc` 初始化，得到
`T=33,298,191`、`P=33,298,193` 的有意义高精度解。当前代码仍保留
`make_single_edge_seed()` 的定义，但初始化流程不再调用它；这属于初始化策略
修复，而不是有理数计算修复。

扫描还说明两点：

- 从 0 到 0.9，权重增加总体上用 precision 换 recall；`1/2` 在已测点中给出
  最高 F1，适合作为平衡默认值。
- 这些是启发式局部搜索轨迹，改变 lambda 也会改变搜索 basin，因此最终 recall
  不保证随权重严格单调；例如 lambda=1 的 recall 略低于 0.9 不是算术矛盾。

## 8. 不应纳入结论的运行

以下目录是 bring-up、失败或不完整记录，不参与算法/性能结论：

- `current-partition-run1`：旧 runner 仍传入已删除的 `coverage` 参数；
- `current-partition-run2`：Python runner 与旧 native extension ABI 不匹配；
- `current-partition-run3`：输入 reference graph metadata 版本不受当前 reader 支持；
- `new-solver-static-gate`、`opt2-sparse-counters`：没有完整 benchmark report；
- `stage-profile`：只用于定位阶段耗时，不是完整正确性基线；
- 所有 180 秒 timeout：只能证明该实现没有在预算内完成，不能用残缺 artifact
  比较解质量。

## 9. OpenMP 与 root-centric admissibility coverage

2026-11-05 的检查发现，原 release build 没有传入 `-fopenmp`：配置虽写 48
threads，RPR 中受 `_OPENMP` 保护的并行路径实际上没有编译，求解器一直串行运行。
新 build 在编译和链接阶段都显式启用 OpenMP，并保留 LTO。

同时完成两项热路径整理：

1. directed admissibility 在构建 symmetric working CSR 时一次性缓存为 `uint8_t`，
   solver 和 admissibility coverage 不再通过 catalog 做数亿次间接查询；
2. summarized admissibility coverage 从“每个 node 扫所有邻居并筛 root”改为“只从
   root 扫 qualifying 邻居”。每个 membership 仍被精确计数一次，
   primary root mapping 是否属于 admissibility coverage 也仍做完整验证。

单线程新实现复现了旧基线的 `T/P`、代表元 identity、membership count 和三个
稳定文件 hash，说明 admissibility coverage/length 改写没有改变语义。48 线程两次运行也得到完全
相同的 `T/P`、代表元 identity 和文件 hash，说明固定线程数下结果确定。并行搜索
轨迹与串行轨迹不同，但最终 F1 从 0.420408811 略升至 0.420540747，所有 partition
audit 和 artifact verifier 均通过。

线程扫描结果如下：

| threads | wall time | peak RSS (GB, 10^9 B) | F1 |
|---:|---:|---:|---:|
| 1 | 69.687 s | 3.782 GB | 0.420408811 |
| 2 | 54.352 s | 3.719 GB | 0.420696308 |
| 4 | 40.160 s | 3.882 GB | 0.420498344 |
| 8 | 28.899 s | 4.066 GB | 0.420588851 |
| 12 | 25.117 s | 4.258 GB | 0.420659926 |
| 24 | 20.554 s | 4.542 GB | 0.420614683 |
| 48 | 18.496 s | 5.043 GB | 0.420540747 |

48 threads 仍是绝对最快点，因此生产合同保持 48，不把用户请求静默限制到较低
线程数。代价是 peak RSS 比串行增加约 1.26 GB；主要来源是 local-move 每线程的
dense counter scratch。最新 perf 中 OpenMP wait/barrier 约占采样的一半，说明
继续增加线程已经进入明显的边际收益区，但 48 相比 24 仍快约 10%。如果未来要
优先控制内存，8 threads 是当前最均衡的替代点。

新基线由 solver v11 的当前二进制直接生成，已消除旧基线“报告 v10、声明 v11”
的 provenance 不一致。

## 决策摘要

| 问题 | 最终选择 | 原因 |
|---|---|---|
| 求解器 | RPR | 旧区域搜索产生近全 singleton 退化解且占用约 20 GB |
| 数值策略 | 精确有理数/交叉乘法 | 修复 v4 的 recall/F1 截断并保证确定性 |
| `recall_weight` | `1/2` | 已测权重中 F1 最好，precision/recall 较平衡 |
| 初始化 | `asc` | 三个候选中 F1 最好 |
| CSR | validated artifact trusted fast path | 最大的单项运行时间收益，输出不变 |
| admissibility coverage | summarized admissibility coverage + primary root mapping | 降低内存，同时保留逐节点 node-to-root 输出 |
| buffer 生命周期 | 尽早释放 canonical buffer | 最大的单项 RSS 收益 |
| counters | dense/current implementation | sparse counters 几乎不省内存且明显变慢 |
| threads | 48 OpenMP | 当前绝对最快；固定线程输出确定，8 threads 是低内存替代点 |
| build | release + LTO | 小幅、可重复加速，RSS 不退化 |
| cost plan | 不进入最终基线 | 收益低于单次 gate，RSS 略高，最终 build 未采用 |

## 10. Independent-root v12 实验（已否决并撤销）

2026-11-05 在相同 schema-4 输入、`asc`、48 threads 和 release profile 下，加入：

- 每轮 Star Project 后的 Independent Root Project；
- Legal `NEW_SINGLETON` root 的 transaction-local dirty frontier；
- 全部 Legal refinement 后的强制 Final Dirty-Root Project；
- 最终 root--root relation verifier。

最初两次 bring-up 运行得到完全相同的 `T/P`、root identity 和三个
稳定结果文件 SHA-256，说明投影实现保持确定性。随后补齐既定优先级中的
`preservedSize`：同 length、同 root 状态时优先保留现有 star 更大的 root。最终
标准运行结果为：

| 项目 | 结果 |
|---|---:|
| wall time | 77.782 s |
| peak RSS | 3,526,877,184 bytes |
| `T` | 44,994,963 |
| `P` | 63,622,938 |
| F1 | 0.366875 |
| roots | 1,222,687 |
| root identity | `99556cd40aa24918` |
| termination | `min_delta_reached` |

最终运行同时记录分阶段时间：

| Root Project | affected nodes | demoted roots | planning | commit |
|---|---:|---:|---:|---:|
| epoch 0 | 1,815,723 | 680,632 | 3.650 s | 2.763 s |
| epoch 1 | 1,578,225 | 527,855 | 3.071 s | 2.646 s |
| final dirty-root | 122,179 | 28,049 | 0.356 s | 0.286 s |

Final Dirty-Root Project 本身不是热点，总耗时约 0.64 秒；热点集中在 epoch
Independent Root Project，且 planning 的串行优先级传播与 commit 的 affected-edge
审计/状态更新成本相近。但更重要的问题不是性能，而是语义和目标质量：强制
roots 构成 independent set 将 F1 从基线的 `0.420409` 降到 `0.366875`。
root--root relation 只表示两个局部 relation neighborhoods 在边界上相邻，并不能
推出两个 stars 应合并；将其视为 feasibility violation 与当前聚类目标冲突。

因此该实验已全面撤销：删除每轮 independent-root projection、dirty-root frontier、
final projection、root--root verifier 及相关统计字段；selection feasibility 恢复为
`length_respecting_direct_star_partition`，允许不同 communities 的 roots 相邻。

撤销后的标准 production benchmark 均通过全部 correctness gate，精确恢复：

| 项目 | 恢复结果 |
|---|---:|
| `T` | 52,492,320 |
| `P` | 68,055,557 |
| F1 | 0.420408811 |
| roots | 1,296,041 |
| root identity | `cfd7c693ba36e7f8` |
| admissibility coverage memberships | 13,089,471 |

三个稳定结果文件的 SHA-256 也与 checked-in v11 baseline 完全一致。最初两次复测
与其他任务并行，wall time 分别为 91.946 s 和 102.255 s，且 epoch 1 从 15.95 s
漂移到 35.99 s；这两次只作为 correctness 证据，不作为性能证据。

清除任务积压后重新运行，wall time 为 **67.254 s**、peak RSS 为
3,877,347,328 bytes，correctness 与 performance gate 全部通过。各轮 total time
依次为 18.047、14.791、15.536、5.233 s；运行中已不存在 independent-root
planning/commit 阶段。因此撤销 root-edge 强制拆分后没有留下可见性能热点。

## 11. Local-move 同步与负载均衡

OpenMP 生产化后，`local_move_sweep` 成为 solver 中最大的可归因热点。
原实现对每个 color 按节点数 `schedule(static)`，但真实工作量接近
$1+\deg(v)$；当 degree 分布不均时，同数量节点会造成明显的 barrier
等待。

2026-11-06 的实现做了三项保持语义的修改：

1. 为每个 full color 预计算正向/反向 degree-weighted 连续分区；
2. proposal、commit 和 persistent-state update 使用同一分区，保留全局
   vertex order、singleton rank 与确定性；
3. 删除可由 OpenMP worksharing/single 隐式保证的重复 barrier，并将
   Legal 的 dirty-frontier 路由合并到 `internalDeg` 邻接扫描中。

最终复测精确保持 `T/P`、root identity、membership count 和
三个稳定文件 hash。标准 wall time 从 19.152 s 降至 17.483 s，peak
RSS 从 5,064,753,152 降至 5,026,648,064 bytes。三轮 Relax 合计从
约 2.148 s 稳定降至约 1.05--1.10 s。Legal 在已测最终构建中合计约
3.00--3.45 s，波动大于可确认改善；本轮主要收益应归因于 full Relax
的 degree-weighted 负载均衡。

同时测试了两个 counter 候选：

- 8192-slot wide hash 将每线程 dense counter 替换为固定开放寻址表，
  RSS 降至约 4.04 GB，但两次 wall time 为 17.65/17.78 s；
- 将 small hash 从 128 扩大到 512 slots 得到 17.64 s。

两者都比 weighted+dense 的最快运行慢，因此生产默认仍保留 128-slot
small hash + dense fallback。wide hash 是有效的低内存候选，但不是当前速度
优先配置。

整体上，partition benchmark 的关键成果不是某一个微优化，而是三层决策共同完成：
先用 RPR 替换不合适的搜索空间，再用精确目标和 initialization/weight 扫描确定
语义选择，最后用 trusted CSR、summarized admissibility coverage、buffer 生命周期和 LTO 把生产
实现压到可接受的时间和内存范围内。
