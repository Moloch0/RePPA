# RPR 工程实现与迁移记录

> 状态：从原下游生产阶段迁入的历史工程记录
> 当前理论：`docs/relax-project-refine.md`
> 当前实现：`rootpart/src/problem.cpp` 与 `rootpart/src/rpr.cpp`

本文保留 RPR 从下游应用中抽取为独立库时形成的实现、性能和审计记录。
其中求解器输入、可行域、目标函数、事务式迭代和最终审计属于 `rootpart`；
产物写出、额外覆盖关系和流水线编排只用于解释历史 benchmark，不构成
`rootpart` 的公开 API，也不向库中引入任何具体应用领域语义。

## 1. 输入契约

`partition_csr()` 直接接收对称 CSR 与逐弧 directed admissibility：

```cpp
struct SparseProblemView {
    std::span<const std::uint64_t> offsets;
    std::span<const NodeId> nodes;
    std::span<const std::uint8_t> arc_admissibility;
    std::uint64_t reference_edges;
};
```

其中：

- `offsets.size() == node_count + 1`；
- `offsets.front() == 0`；
- `offsets.back() == nodes.size()`；
- 每条无向边在 adjacency 中出现两个方向；
- `reference_edges` 是无向边数 $m$；
- 节点 ID 必须可由 `uint32_t` 表示；
- bit `0x01` 表示 CSR row source 可作为 neighbor 的 root；
- bit `0x02` 表示 neighbor 可作为 CSR row source 的 root。

求解器直接读取该 CSR，不创建第二张可行性图。

## 2. Directed-admissible rooted partition 可行域

一个分区由若干 star block 构成。每个 block 有唯一 root $r$，每个非 root 成员 $v$ 必须满足：

1. $\{r,v\}\in E$；
2. directed admissibility 中允许 $r$ represent $v$。

root 自身总是合法成员。最终 root mapping 为每个节点记录其唯一 root。
不同 communities 的 roots 之间允许存在 relation edge；roots 不要求构成
relation graph 的 independent set。root--root relation 只表示两个局部邻域在边界上
存在直接关系，不足以推出两个 stars 应被强制合并。

admissibility 不是写出阶段的补充检查，而是参与全部候选选择：

- 初始化吸附成员；
- Relax destination 选择；
- Project root 选择与保留成员选择；
- Legal relocation；
- 最终完整校验。

## 3. 目标函数

设：

- $m=|E|$：reference relation edges；
- $T$：分区内部 relation edges；
- $P=\sum_C {|C|\choose 2}$：分区预测的同组 pair 数；
- $\lambda=a/b\in[0,1]$，且为约分后的精确有理数。

目标为：

$$
J_\lambda=
\frac{bT}{am+(b-a)P}.
$$

epoch acceptance 和停止阈值判断均使用精确整数运算，不通过浮点数决定。

边界值语义：

- $\lambda=0$：目标退化为 precision $T/P$；有边图会额外构造一个合法单边 seed，保证 Phase I 的 $P>0$；
- $\lambda=1$：目标退化为 recall $T/m$；
- $m=0$：返回全单例分区，precision、recall、F1 均记为未定义。

## 4. 初始化

默认初始化模式为 `asc`。求解器支持：

- `desc`：按 degree 降序访问候选 root；
- `asc`：反向访问同一排序；
- `local`：选择局部高优先级 root；

degree 相同时，以较小的 canonical `NodeId` 决定稳定顺序。

一次运行只使用请求的一个 seed，并对该 seed 重算精确 $T/P$。当前公开 API 不提供同时评估多个 seeds 的 `all` 模式。

## 5. Relax–Project–Refine

最多执行 `max_epochs` 个完整 epoch。每个 epoch 固定执行：

```text
accepted incumbent
    -> begin transaction
    -> Relax
    -> Project
    -> Legal
    -> exact objective comparison
       -> commit and test min_delta
       -> or rollback and terminate
```

默认 `max_epochs=5`、`min_delta=1/100`、`threads=48`。令

$$
\Delta J=J_\lambda(\mathcal P_{\mathrm{new}})-
J_\lambda(\mathcal P_{\mathrm{old}}).
$$

- $\Delta J\le 0$：rollback 并终止 epoch search；
- $0<\Delta J<\texttt{min\_delta}$：接受该正向改善，然后终止 epoch search；
- $\Delta J\ge\texttt{min\_delta}$：接受并继续，直到达到 `max_epochs`。

`min_delta=0` 表示只要仍有严格改善就继续，`max_epochs` 仍是硬上限。

### 5.1 Relax

Relax 暂时允许一般 partition block。每个 epoch 固定执行一次 relocation sweep：

- 按固定 graph coloring 分批处理独立集；每个 full color 在初始化时
  按 $1+\deg(v)$ 预计算确定性连续分区，同时保留正向和反向访问顺序；
- 扫描节点 adjacency，聚合目标 community 的邻接计数；
- 在当前 epoch 的固定 objective anchor 下计算精确增益；
- 通过 owner-computes reduction 更新 community size、$T$ 和 $P$；
- 保持确定性的候选顺序和 tie-break。

当前实现的 Relax 是 full streaming sweep。

### 5.2 Project

Project 将 Relax 后的每个 changed community 投影回 legal star：

- root 候选必须是该 community 的成员；
- root 只能保留与其相邻且满足 root-to-member admissibility 的成员；
- 选择可保留成员数最多的 root；
- 平局选择较小的 canonical `NodeId`；
- 未被保留的成员转为 singleton community。

首次 Project 前构建的 persistent membership/internal-degree cache 计入该轮 Project 耗时。

### 5.3 Legal

Legal 只在 admissible rooted partition 可行域内执行 relocation：

- 目标 community 必须有有效 root；
- moving node 必须与目标 root 相邻；
- 目标 root 必须对 moving node admissible；
- 增益与 acceptance 均使用当前 epoch 的精确 anchor。

生产实现只使用 transaction changes 派生的精确/保守动态 pending frontier。变化稠密时，frontier 自动扩展为全部节点，不提供手工 full-scan 开关。
已接受 move 在维护 `internalDeg` 时会同步路由 moving node 及其邻居的
dirty records，不再为 frontier invalidation 第二次扫描同一份 adjacency。

epoch search 结束后执行最终 Legal refinement。每次 refinement sweep：

1. 从当前 legal incumbent 建立新的 objective anchor；
2. 在独立 transaction 中执行一次动态 Legal sweep；
3. 仅在真实 $J_\lambda$ 严格改善时提交；
4. 若正向改善小于 `min_delta`，接受该改善后停止，否则继续。

因此最终 Legal 不使用固定 sweep 数，与 epoch search 共享同一个 `min_delta`。

### 5.4 Commit 与 rollback

若 candidate 严格改善 $J_\lambda$：

- 提交 transaction；
- candidate 成为下一轮 incumbent；
- 再由 `min_delta` 决定是否继续搜索。

否则：

- 恢复 community root 和 membership；
- 重建 size、free IDs 和 persistent cache；
- 终止 epoch search。

## 6. 最终验证

求解结束后无条件执行最终验证：

1. 每个 root mapping root 在节点范围内；
2. 每个非 root 成员满足 directed admissibility；
3. 每个非 root 成员与 root 存在 relation edge；
4. 全图重算的 $T/P$ 与在线 audit 一致。

验证通过后才构造 `PartitionResult`。`roots` 按 canonical `NodeId` 排序，
`root_of` 覆盖完整 node universe。

## 7. 历史下游流水线

抽取前的下游流水线大致按以下顺序执行：

```text
validate configuration and relation artifact
    -> load AdmissibilityView
    -> build SymmetricWorkingCsr
    -> optimize admissible rooted partition
    -> summarize final complete admissibility-respecting admissibility coverage
    -> build diagnostics
    -> validate and write representation artifact
```

完整 admissibility coverage 与 primary root mapping 是不同产物：

- primary root mapping 记录求解器选择的唯一 root；
- complete admissibility coverage 枚举每个 member 可由哪些 selected roots 合法覆盖。

生产链路只从已经验证的 `SymmetricWorkingCsr` 构造 complete admissibility coverage。旧的
exact-pair、reference graph/reference admissibility coverage builder 不再作为公开接口或备用路径保留，
从而保证分区、最终验证与 admissibility coverage 使用同一份 canonical `NodeId` 图坐标。
working CSR 同时缓存每个 node 的紧凑 `uint8_t` directed admissibility，solver
和 admissibility coverage 的热路径不再重复经过 catalog 间接查询。

summarized admissibility coverage 按 selected root 扫描邻接表：每个 root
先计入 self-membership，再计入满足 admissibility relation 的邻居。这与“每个
member 扫描所有邻居并筛 root”的 membership 集合完全等价，
但不再访问与最终 root set 无关的边。实现仍独立验证每个
primary root mapping 的 selected root 确实出现在该 member 的 admissibility coverage 中。

complete admissibility coverage 在 `partition` 中只保留完整性、membership count 与 root mapping projection 的摘要，
不物化 per-node memberships。生产结果固定写出 roots、compact primary root mapping 与
两项 summary diagnostics。需要“每个 member 可由哪些 roots 覆盖”的完整列表时，使用独立的
`export-admissibility coverage DATABASE TOPOLOGY REPRESENTATION OUTPUT` 后处理；它重新读取 reference graph 与
roots，默认输出紧凑 CSR，也可显式输出 TSV，因此不会扩大默认 representation artifact。
`roots.tsv` 是 root 列表和后续 admissibility coverage 计数的权威数据源；
representation `metadata.json` 只用于验证 artifact 类型、node universe、
relation semantics 与 policy 兼容性，其中的 count 不参与内存分配或 admissibility coverage 计算。

CSR 产物包含：

- `offsets.u64`：`node_count + 1` 个 little-endian `uint64`；
- `roots.u32`：按 member NodeId 分段、段内按 root NodeId 升序排列；
- `metadata.json`：绑定 node universe fingerprint、relation semantics、root-set identity 与 checksums。

查询 member `i` 时，只需读取 `offsets[i:i+2]`，再读取对应的 `roots.u32` slice。
不计 metadata 时，CSR payload 大小固定为
$8(N+1)+4M_C$ bytes，其中 $M_C$ 是 complete-admissibility coverage membership count；TSV 只用于互操作，通常更大。

## 8. 统计契约

Python 默认返回值只包含 node/root 数、最终 precision/recall/F1、实际 epoch 数和 termination reason。精确 `m/T/P` 与逐轮统计只在 `diagnostics=True`（CLI 为 `--diagnostics`）时返回。

最终字段：

```text
lambda
m
T
P
precision
recall
f1
rounds
```

精确比例表示为：

```json
{"numerator": A, "denominator": B}
```

未定义指标表示为 `null`。

`rounds` 中每个元素包含：

```text
round
precision
recall
f1
relax_wall_ns
project_wall_ns
legal_wall_ns
total_wall_ns
accepted
```

被拒绝轮记录的是 rollback 前 candidate 的指标与耗时，`accepted=false` 明确其未成为最终 incumbent。

## 9. 历史 artifact 审计与 provenance

representation result 使用 root artifact schema 4、representation domain schema 3。节点排序只由
canonical `NodeId` 表达，TSV 不再重复保存 rank：

- `roots.tsv`：`representative_id, sequence_length`；
- `root_of.tsv`：固定为 `member_id, representative_id`；
- complete admissibility coverage 默认不落盘；可由 `export-admissibility coverage` 单独导出。

旧 schema 产物不兼容，必须重新执行相应阶段。

`partition_audit` 只保存：

```text
recall_weight
reference_edges
true_positive_edges
predicted_pairs
precision
recall
f1
```

写出前验证：

$$
T\le m,
\qquad
T\le P.
$$

`partition_search` 保存当前求解器身份、请求的 initialization、实际选中的 initial incumbent、目标/可行性/数值策略、`max_epochs`、精确 `min_delta`、确定性声明和终止原因。

## 10. 终止原因

当前终止原因只有：

- `no_strict_improvement`；
- `min_delta_reached`；
- `max_epochs_reached`；
- `objective_undefined_no_reference_edges`。

## 11. 复杂度

基础 persistent memory 为：

$$
O(n+m).
$$

低 degree 图使用固定容量 thread-local hash；高 degree 图可能使用 thread-local dense counters，最坏增加 $O(pn)$ 空间，其中 $p$ 为 OpenMP thread 数。

一次 full Relax sweep 和一次全量验证均为 $O(n+m)$。Project 的主要成本与 changed communities、候选 root adjacency 和 peeled vertices 相关。

## 12. 源码职责

| 文件 | 职责 |
|---|---|
| `rootpart/rootpart/src/rpr.cpp` | 初始化、Relax、Project、Legal、transaction 和精确分区审计 |
| `src/partition/symmetric_csr.cpp` | 从 canonical relation edges 构造共享对称 CSR，并把长度规则编码成 directed admissibility bits |
| `src/partition/rootpart_adapter.cpp` | rootpart 输入/输出与 downstream consumer representation 类型之间的薄适配 |
| `src/partition/partition.cpp` | 公开 partition 入口及生产阶段编排 |
| `downstream adapter: admissibility coverage` | 按 root adjacency 汇总最终完整 admissibility-respecting admissibility coverage |
| `downstream adapter: coverage export` | 从 reference graph 与 representation roots 流式导出完整 admissibility coverage |
| `downstream adapter: artifact writer` | 验证并写出 representation artifact |
| `src/module.cpp` | Python 参数绑定和统计序列化 |

当前 partition 没有第二套分区求解入口、替代初始化 API 或备用 admissibility coverage builder。后续优化必须保持 admissible rooted partition 可行性、精确 objective acceptance、完整 rollback 和上述统计契约。
