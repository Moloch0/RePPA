
# Admissible Rooted Partitioning：Relax–Project–Refine 理论骨架

## 一、问题定义：Legal-Star Partition 与 $J_\lambda$

给定无向 reference graph，以及定义在 reference edges 两个方向上的
root admissibility relation：

$$
G=(V,E),\qquad
A\subseteq\{(u,v):\{u,v\}\in E\},\qquad
n=|V|,\qquad m=|E|.
$$

$(r,v)\in A$ 表示节点 $r$ 可以作为节点 $v$ 的 root。定义

$$
A^+(r)=\{v:(r,v)\in A\}.
$$

最终输出一个节点 partition：

$$
\mathcal P=\{S_1,S_2,\ldots,S_k\}.
$$

每个 partition $S$ 必须能够表示成一个 legal star，即存在一个 representative / root $r\in S$，使得

$$
\forall v\in S\setminus\{r\},\qquad (r,v)\in A.
$$

因此一个 legal star 可以写成 $(r,S)$。singleton $\{v\}$ 天然合法，并以 $v$ 自身作为 root。

不同 legal stars 的 roots 允许相邻。边 $\{r_i,r_j\}\in E$ 只说明两个
representatives 之间存在局部 relation；由于 relation 不具传递性，它并不推出
$S_i\cup S_j$ 应构成同一个 cluster。因此 representative 集合不要求是 independent
set，root--root edge 也不构成 feasibility violation。

一个 partition $S$ 表示 clique prediction：只要两个节点属于同一个 partition，就预测它们之间存在 relation。

定义 partition 内真实 relation edge 数：

$$
T(\mathcal P)=\sum_{S\in\mathcal P} e(S),
$$

以及 predicted-positive pair 数：

$$
P(\mathcal P)=\sum_{S\in\mathcal P}\binom{|S|}{2}.
$$

于是

$$
FP=P-T,\qquad FN=m-T,
$$

标准 pairwise $F_1$ 为

$$
\boxed{
F_1(\mathcal P)=\frac{2T}{m+P}.
}
$$

为了显式控制 precision--recall trade-off，引入外部 policy parameter

$$
\boxed{\lambda\in[0,1]}
$$

并定义统一的 ratio objective

$$
\boxed{
J_\lambda(\mathcal P)
=
\frac{T(\mathcal P)}
{\lambda m+(1-\lambda)P(\mathcal P)}.
}
$$

三个关键 operating points 为

$$
\boxed{
\lambda=0:\ \frac{T}{P}\ \text{(precision)},
\qquad
\lambda=\frac12:\ J_{1/2}=F_1,
\qquad
\lambda=1:\ \frac{T}{m}\ \text{(recall)}.
}
$$

$\lambda=0$ 时 objective 只在 $P>0$ 的 partition 上有定义；$\lambda=1$ 时 $P$ 不再进入 primary objective。除端点特别说明外，后续 ratio 推导默认 denominator 为正。

所以整个优化问题只依赖于两个统计量：

$$
\boxed{T,\qquad P.}
$$

---

# 二、Ratio Objective、Anchored Objective 与 Exact Gain

假设当前 partition 的统计量为 $T,P$，某个变化产生

$$
\Delta T,\qquad \Delta P.
$$

记当前 denominator 为

$$
D_\lambda
=
\lambda m+(1-\lambda)P.
$$

变化后的 $J_\lambda$ 改善，当且仅当

$$
\frac{T+\Delta T}
{D_\lambda+(1-\lambda)\Delta P}
>
\frac{T}{D_\lambda}.
$$

交叉相乘得

$$
D_\lambda\Delta T
-
T(1-\lambda)\Delta P
>0.
$$

定义当前 ratio anchor 与有效 pair penalty

$$
\boxed{
\eta
=
\frac{T}{D_\lambda}
=
J_\lambda,
\qquad
\gamma
=
(1-\lambda)\eta.
}
$$

则

$$
\boxed{
J_\lambda'>J_\lambda
\iff
\Delta T-\gamma\Delta P>0.
}
$$

因此，在固定当前 $(\eta,\lambda)$，等价地固定 $\gamma$ 时，可以使用 additive objective

$$
\boxed{
L_\gamma(\mathcal P)
=
T(\mathcal P)-\gamma P(\mathcal P).
}
$$

令

$$
x_{uv}
=
\mathbf 1[u,v\text{ 属于同一 partition}],
$$

则

$$
T=\sum_{u<v}\mathbf1_{\{u,v\}\in E}x_{uv},
\qquad
P=\sum_{u<v}x_{uv},
$$

所以

$$
\boxed{
L_\gamma
=
\sum_{u<v}
\left(
\mathbf1_{\{u,v\}\in E}-\gamma
\right)x_{uv}.
}
$$

因此一个 co-membership pair 的贡献为

$$
\begin{cases}
1-\gamma,&\{u,v\}\in E,\\[1mm]
-\gamma,&\{u,v\}\notin E.
\end{cases}
$$

对单个 partition $S$，定义

$$
\boxed{
\phi_\gamma(S)
=
e(S)-\gamma\binom{|S|}{2}.
}
$$

于是

$$
\boxed{
L_\gamma(\mathcal P)
=
\sum_{S\in\mathcal P}\phi_\gamma(S).
}
$$

这正是 Constant Potts Model 的形式，其中 resolution parameter 对应有效 pair penalty

$$
\boxed{
\gamma
=
(1-\lambda)J_\lambda(\mathcal P).
}
$$

$\lambda$ 是外部 policy parameter；$\eta$ 是当前 partition 的 ratio value；$\gamma$ 则由二者共同决定，不是另一个独立 hyperparameter。

特别地，当 $\lambda=1/2$ 时，

$$
\eta=F_1,
\qquad
\gamma=\frac{F_1}{2}=\frac{T}{m+P},
$$

因此完整恢复原始 F1 anchored objective。

---

## 2.1 Relaxed 与 Legal 两个搜索空间

定义无约束 partition 空间

$$
\Omega_{\mathrm{relaxed}}
=
\{\text{所有 }V\text{ 的 partitions}\},
$$

以及 legal-star 空间

$$
\Omega_{\mathrm{legal}}
=
\left\{
\mathcal P:
\forall S\in\mathcal P,\,
\exists r\in S,\,
S\setminus\{r\}\subseteq A^+(r)
\right\}.
$$

显然

$$
\boxed{
\Omega_{\mathrm{legal}}
\subseteq
\Omega_{\mathrm{relaxed}}.
}
$$

两个空间中的 objective 都是同一个

$$
L_\gamma=T-\gamma P,
$$

区别只在 feasibility constraint。

因此可以使用同一个 node-relocation / FM optimization engine，只改变 candidate legality。

---

## 2.2 Single-Node Move 的 Exact Gain

考虑节点

$$
v\in S_p
$$

移动到另一个 partition $S_q$。

令

$$
n_p=|S_p|,
\qquad
n_q=|S_q|,
$$

并定义

$$
d(v,S)=|N(v)\cap S|.
$$

由于移动时只有涉及 $v$ 的 co-membership pair 发生变化，

$$
\boxed{
\Delta T
=
d(v,S_q)
-
d(v,S_p\setminus\{v\}).
}
$$

同时

$$
\boxed{
\Delta P=n_q-n_p+1.
}
$$

所以 fixed-anchor exact gain 为

$$
\boxed{
g(v:p\to q)
=
d(v,S_q)
-
d(v,S_p\setminus\{v\})
-
\gamma(n_q-n_p+1).
}
$$

也可以写成

$$
g(v:p\to q)
=
\underbrace{
\gamma(n_p-1)
-d(v,S_p\setminus\{v\})
}_{\text{source term}}
+
\underbrace{
d(v,S_q)-\gamma n_q
}_{\text{destination term}}.
$$

对于固定节点 $v$，source term 已经确定，因此选择 destination 等价于最大化

$$
\boxed{
H_v(q)=d(v,S_q)-\gamma n_q.
}
$$

singleton creation 只是 $n_q=0$、$d(v,S_q)=0$ 的普通 destination，因此

$$
\boxed{
g_{\mathrm{singleton}}(v)
=
\gamma(n_p-1)
-
d(v,S_p\setminus\{v\}).
}
$$

这个 gain formula 同时适用于 relaxed FM 和 legal FM。两者的唯一区别是哪些 destination 合法。

---

# 三、Legal-Star Constraint 的核心困难：Leaf 容易，Root 困难

## 3.1 Leaf Relocation

假设当前 legal star 为

$$
(r_p,S_p).
$$

若

$$
v\in S_p,\qquad v\neq r_p,
$$

则 $v$ 是 leaf。

$v$ 离开以后，$r_p$ 仍留在 source partition，因此 source star 自动保持合法。

如果 $v$ 想进入另一个 star

$$
(r_q,S_q),
$$

只需满足

$$
\boxed{
\{v,r_q\}\in E.
}
$$

因此 leaf relocation 的 feasibility 判断只依赖一条 representative edge，而 objective gain 仍然由上一节的 exact node gain 给出。

所以 leaf relocation 是一个真正的一阶局部操作。

---

## 3.2 Root Restructuring 不是 Ordinary Node Move

考虑当前 root $r$，假设希望另一个节点 $q$ 成为新 root。

新的状态不能只写成

$$
r\to q,
$$

因为 $q$ 还必须同时决定新的 leaf set

$$
L'\subseteq N(q).
$$

新的 star 为

$$
\{q\}\cup L'.
$$

其 anchored contribution 为

$$
\phi_\gamma(q,L')
=
|L'|+e(L')
-
\gamma\binom{|L'|+1}{2},
$$

即

$$
\boxed{
\phi_\gamma(q,L')
=
(1-\gamma)|L'|
+
e(L')
-
\gamma\binom{|L'|}{2}.
}
$$

关键项是

$$
\boxed{e(L').}
$$

因此不同候选 leaves 之间存在 pairwise interaction。

两个节点分别适合作为 $q$ 的 leaf，并不意味着它们同时加入后仍然最优。因此 root quality 不存在一个类似

$$
d(q,S)-\gamma|S|
$$

的一阶 scalar score。

选择一个新 root，实际上隐含着同时重新选择一组 leaves。

所以：

$$
\boxed{
\text{root restructuring 本质上是局部 subset-selection problem，}
}
$$

而不是普通 node relocation。

---

## 3.3 为什么不能永久固定 Root

如果 legal FM 从头到尾固定所有 roots，搜索空间会被显著 pin 住。

某个节点 $v$ 可能不与当前 root $r_p$ 相邻，因此无法进入 $S_p$；但如果未来该区域由另一个节点 $q$ 作为 root，则可能有

$$
v\sim q.
$$

因此当前 root identity 会直接限制 partition 能够演化到的状态。

于是产生一个两难：

$$
\boxed{
\text{永久固定 root 会人为限制搜索空间；}
}
$$

但

$$
\boxed{
\text{精确优化 root 又会引入 leaf-subset combinatorics。}
}
$$

因此不再设计复杂 atomic root move，而采用周期性解除 legal-star constraint，让 membership 在 relaxed 空间中重新组织，再重新生成 roots。

这就是 Relax–Project–Refine 的核心动机。

---

# 四、统一的 FM Optimization Framework

Single-node gain 是 exact 的，但多个 moves 之间存在 interaction。

如果先执行

$$
u:S_a\to S_b,
$$

那么 $S_a,S_b$ 的大小会变化；同时对于

$$
v\in N(u),
$$

其

$$
d(v,S_a),\qquad d(v,S_b)
$$

也会变化。

因此：

$$
\boxed{
\text{单步 gain exact，但旧 gain 不能跨状态直接累加。}
}
$$

FM 通过 move-sequence search 处理这种 interaction。

设一个 pass 中执行

$$
M_1,M_2,\ldots,M_t.
$$

每执行一步，都基于当前最新状态重新获得后续 move 的 exact gain。允许某些 move 暂时具有负 gain，最后只接受累计 gain 最好的 prefix。

因此 FM 用 sequential relocation search 代替显式 subset enumeration。

---

## 4.1 Fixed-$(\eta,\lambda)$ FM Pass 与 Best Prefix

设一个 FM pass 的起始状态为

$$
(T_0,P_0),
$$

定义

$$
D_{\lambda,0}
=
\lambda m+(1-\lambda)P_0,
$$

$$
\eta_0
=
\frac{T_0}{D_{\lambda,0}},
\qquad
\gamma_0
=
(1-\lambda)\eta_0.
$$

第 $i$ 个 move 的 gain 为

$$
g_i=\Delta T_i-\gamma_0\Delta P_i.
$$

前 $k$ 个 moves 的累计 gain 为

$$
G_k=\sum_{i=1}^k g_i.
$$

于是

$$
G_k
=
(T_k-T_0)
-
\gamma_0(P_k-P_0).
$$

由于

$$
T_0=\eta_0D_{\lambda,0},
$$

有

$$
\boxed{
G_k>0
\iff
\frac{T_k}{\lambda m+(1-\lambda)P_k}
>
\frac{T_0}{\lambda m+(1-\lambda)P_0}.
}
$$

因此一个 FM pass 内固定 $(\eta_0,\lambda)$，等价地固定 $\gamma_0$ 时，cumulative gain 对 $J_\lambda$ 的 best-prefix selection 仍然是 exact 的。

所以自然的更新层级是

$$
\boxed{
\text{全程固定 }\lambda;
\qquad
\text{FM pass 内固定 }\eta,\gamma;
\qquad
\text{pass 接受后重新计算 }\eta,\gamma.
}
$$

---

## 4.2 Relaxed Mode 的 Candidate Set

在 relaxed mode 中，没有 root / leaf distinction。

节点 $v$ 可以进入任意满足

$$
d(v,S)>0
$$

的 partition，或者创建 singleton。

如果一个非空 partition $S$ 满足

$$
d(v,S)=0,
$$

那么 destination term 为

$$
H_v(S)=-\gamma|S|\le 0,
$$

而 singleton destination 有

$$
H_v(\varnothing)=0.
$$

所以无连接的非空 partition 永远不会优于 singleton。

因此只需考虑

$$
\boxed{
\mathcal C_{\mathrm{relaxed}}(v)
=
\{S:d(v,S)>0\}
\cup
\{\varnothing\}.
}
$$

---

## 4.3 Legal Mode 的 Candidate Set

在 legal mode 中，若 destination star 为

$$
(r_q,S_q),
$$

则节点 $v$ 必须满足

$$
\boxed{
\{v,r_q\}\in E.
}
$$

所以

$$
\boxed{
\mathcal C_{\mathrm{legal}}(v)
=
\{
S_q:r_q\in N(v)
\}
\cup
\{\varnothing\}.
}
$$

gain formula 在两种 mode 中完全相同，只有 candidate filtering 不同。

因此可以统一写成

$$
\operatorname{FM}
(
\mathcal P,
\gamma=(1-\lambda)\eta,
\operatorname{candidate\_predicate}
).
$$

---

# 五、Relax–Project–Refine

## 5.1 Relaxed CPM-FM：解除 Root Pinning

设当前有一个 legal incumbent

$$
\mathcal P^{(t)}
\in
\Omega_{\mathrm{legal}}.
$$

计算当前 ratio anchor 与有效 pair penalty

$$
\boxed{
\eta_t
=
\frac{
T(\mathcal P^{(t)})
}{
\lambda m+(1-\lambda)P(\mathcal P^{(t)})
},
\qquad
\gamma_t
=
(1-\lambda)\eta_t.
}
$$

在当前 epoch 中固定

$$
(\eta,\gamma)=(\eta_t,\gamma_t).
$$

然后删除所有 root labels，只保留当前 membership partition。

此时搜索空间从

$$
\Omega_{\mathrm{legal}}
$$

扩张到

$$
\Omega_{\mathrm{relaxed}}.
$$

运行

$$
\boxed{
\widetilde{\mathcal P}^{(t)}
=
\operatorname{FM}_{\mathrm{relaxed}}
(
\mathcal P^{(t)},
\gamma_t
).
}
$$

在这一阶段：

- 没有 root；
- 没有 leaf；
- 所有节点完全对称；
- 原来的 representative 不再具有特殊身份；
- membership 可以跨过 root legality 造成的 barrier。

relaxed phase 的作用不是直接“优化 root”，而是暂时取消 root 结构上的硬约束。

因此 root change 不再通过显式

$$
r\to q
$$

实现，而通过

$$
\mathcal P
\longrightarrow
\widetilde{\mathcal P}
\longrightarrow
\text{重新 projection}
$$

自然发生。

---

## 5.2 Star Projection：恢复 Legal-Star Feasibility

relaxed FM 得到

$$
\widetilde{\mathcal P}
=
\{C_1,C_2,\ldots,C_k\}.
$$

一个 relaxed block $C$ 不一定存在能够连接全部成员的 root。

对于任意

$$
r\in C,
$$

定义其 block 内 degree

$$
d_C(r)=d(r,C).
$$

若选择 $r$ 为 root，则它能够合法保留的最大节点集合为

$$
\boxed{
S_r
=
\{r\}
\cup
\left(
A^+(r)\cap C
\right).
}
$$

其大小为

$$
|S_r|=1+d_C(r).
$$

因此被剥离的节点数为

$$
|C|-1-d_C(r).
$$

自然的 projection root 为

$$
\boxed{
r^*
=
\arg\max_{r\in C}
d_C(r).
}
$$

然后保留

$$
\boxed{
S_{r^*}
=
\{r^*\}
\cup
(A^+(r^*)\cap C),
}
$$

其余节点

$$
C\setminus S_{r^*}
$$

暂时成为 singleton。

定义 star-feasibility defect

$$
\boxed{
\delta(C)
=
|C|-1-
\max_{r\in C}d_C(r).
}
$$

则

$$
\boxed{
\delta(C)=0
\iff
C\text{ 自身已经是 legal star}.
}
$$

同时 $\delta(C)$ 恰好是使用最佳 internal-degree root 时至少需要剥离的节点数。

于是定义 projection operator

$$
\boxed{
\Pi_{\mathrm{star}}
:
\Omega_{\mathrm{relaxed}}
\rightarrow
\Omega_{\mathrm{legal}}.
}
$$

并令

$$
\boxed{
\widehat{\mathcal P}^{(t)}
=
\Pi_{\mathrm{star}}
(
\widetilde{\mathcal P}^{(t)}
).
}
$$

需要强调的是，

$$
r^*=\arg\max d_C(r)
$$

最大化的是一次 projection 中能够合法保留的节点数量，等价于最小化 $\delta(C)$。

它并不保证最大化 projection 后的 $L_\gamma$。

如果要求 objective-optimal projection，就会重新引入 neighborhood-induced pair interaction。因此这里刻意采用便宜、确定、只依赖一阶信息的 feasibility projection。

objective recovery 留给下一阶段。

---

## 5.3 Legal FM：在新 Roots 下精细调整

projection 后

$$
\widehat{\mathcal P}^{(t)}
\in
\Omega_{\mathrm{legal}}.
$$

每个非-singleton star 已经具有明确 root，被剥离的节点暂时成为 singleton。

现在运行 legal FM。

如果

$$
v\neq r_p,
$$

则 $v$ 是 leaf，可以从

$$
S_p\to S_q
$$

只要

$$
\{v,r_q\}\in E.
$$

也可以移动到 singleton。

singleton 节点自身就是 root，因此也可以进入任何对其满足 directed
root admissibility 的合法 destination。

非-singleton root 在 legal FM 中不作为 ordinary relocation node 离开。

这意味着 legal FM 暂时固定当前 roots。

这是有意的：root 的大尺度变化已经交给下一轮 relaxed phase，而 legal FM 的职责是

$$
\boxed{
\text{在给定当前 roots 的条件下，将 membership 调整到好的 legal local optimum。}
}
$$

具体包括：

- 将 projection 剥离出的 singleton 重新吸收到合适 stars；
- 在 stars 之间重新分配 leaves；
- 删除不合适的 leaves；
- 恢复 projection 为追求 feasibility 而牺牲的 objective quality。

因此

$$
\boxed{
\text{Projection 恢复 feasibility；
Legal FM 恢复 objective quality。}
}
$$

最终得到

$$
\boxed{
\mathcal Q^{(t)}
=
\operatorname{FM}_{\mathrm{legal}}
(
\widehat{\mathcal P}^{(t)},
\gamma_t
).
}
$$

---

# 六、初始化与 Anchor 更新

算法仍然需要一个初始 legal partition

$$
\mathcal P_0.
$$

初始化真正决定的是

$$
\boxed{
\mathcal P_0
\Longrightarrow
(T_0,P_0)
\Longrightarrow
(\eta_0,\gamma_0).
}
$$

其中

$$
\boxed{
\eta_0
=
\frac{T(\mathcal P_0)}
{\lambda m+(1-\lambda)P(\mathcal P_0)},
\qquad
\gamma_0=(1-\lambda)\eta_0.
}
$$

因此 partition seed 与 resolution seed 不是两个独立问题。

---

## 6.1 $\lambda$、$\eta$ 与 $\gamma$ 的角色

$\lambda$ 是控制 precision--recall trade-off 的外部 policy parameter。固定 $\lambda$ 后，原始优化目标是

$$
\boxed{
\max_{\mathcal P}
J_\lambda(\mathcal P)
=
\frac{T(\mathcal P)}
{\lambda m+(1-\lambda)P(\mathcal P)}.
}
$$

当前 partition 决定动态 ratio anchor

$$
\boxed{
\eta(\mathcal P)=J_\lambda(\mathcal P),
}
$$

以及 fixed-anchor 子问题真正使用的 CPM resolution

$$
\boxed{
\gamma(\mathcal P)
=
(1-\lambda)\eta(\mathcal P).
}
$$

因此 $\eta$ 与 $\gamma$ 都不是额外 hyperparameter；$L_\gamma$ 只是 $J_\lambda$ 在 fixed anchor 下的 additive representation。

---

## 6.2 为什么不从全 Singleton 开始

全 singleton partition

$$
\mathcal P_{\mathrm{singleton}}
=
\{\{v\}:v\in V\}
$$

当然合法。

但此时

$$
T=0,\qquad P=0,
$$

对于 $0<\lambda\le1$ 且 $m>0$，所以

$$
\eta=0,
\qquad
\gamma=0.
$$

第一轮 anchored objective 退化为

$$
L_0=T,
$$

对应的 gain 只有

$$
g=\Delta T.
$$

此时 $\Delta P$ 完全没有代价，因此第一轮优化只关心将多少 relation edges 放入同一个 partition，而不惩罚由此产生的 false-positive pairs。

这会带来明显的 coarse aggregation bias。

因此全 singleton 虽然合法，但不是理想的默认初始化。

当 $\lambda=0$ 时，全 singleton 的 $P=0$ 使 pure-precision objective 未定义，因此不能用它建立初始 anchor；此时必须从某个 $P>0$ 的 legal seed 开始。若不存在这样的 legal partition，则 pure-precision endpoint 本身没有定义。

---

## 6.3 一阶 Legal-Star Cover

可以保留三个廉价的一阶 initialization。

### Degree-descending greedy star cover

按照 $d(v)$ 从大到小访问节点。

若 $r$ 尚未分配，则令其成为 root，并吸收所有尚未分配的邻居：

$$
\boxed{
S_r
=
\{r\}
\cup
\{v\in A^+(r):v\text{ 尚未分配}\}.
}
$$

该方法偏向高-degree center 和较大的 initial stars。

### Degree-ascending greedy star cover

过程相同，但按 $d(v)$ 从小到大访问。

它偏向较小 stars 和 peripheral centers。

### Local-degree-maximum assignment

令

$$
\pi(v)
=
(d(v),-\operatorname{rank}(v)).
$$

局部 precedence maximum 成为 root candidate，其他节点从相邻 roots 中选择 precedence 最大者，没有相邻 root 的节点保持 singleton。

该方法偏向局部 center selection，并减少全局 ordering dependence。

这些方法都只依赖 degree 和 adjacency，因此可以保持

$$
\boxed{O(n+m)}
$$

量级。

---

## 6.4 Initialization 策略选择

`desc`、`asc` 和 `local` 是三个独立的初始化策略。一次求解只选择其中
一个 seed，并从该 seed 运行一条完整的 Relax–Project–Refine trajectory；
求解器不在单次调用中执行组合 multi-start。

不同初始化会同时改变 relaxed FM 的 starting basin、第一轮 CPM
resolution，以及初始 legal-star structure 的尺度。因此，比较策略时应在
相同输入和参数下分别运行完整求解，再比较最终 legal partition 的 exact
audit。当前生产默认值为 `asc`。

---

# 七、Outer Alternating Optimization 与 Exact Acceptance

设当前 legal incumbent 为

$$
\mathcal P^{(t)}.
$$

计算

$$
\boxed{
\eta_t
=
\frac{
T(\mathcal P^{(t)})
}{
\lambda m+(1-\lambda)P(\mathcal P^{(t)})
},
\qquad
\gamma_t=(1-\lambda)\eta_t.
}
$$

然后固定该 anchor，执行

$$
\boxed{
\mathcal P^{(t)}
\xrightarrow{\text{Relaxed FM}}
\widetilde{\mathcal P}^{(t)}
\xrightarrow{\text{Star Projection}}
\widehat{\mathcal P}^{(t)}
\xrightarrow{\text{Legal FM}}
\mathcal Q^{(t)}.
}
$$

其中

$$
\mathcal Q^{(t)}
\in
\Omega_{\mathrm{legal}}.
$$

由于 relaxed 中间状态不满足最终约束，而且 projection 可能造成 objective loss，因此 relaxed objective 的改善不能保证最终 legal $J_\lambda$ 改善。

所以始终保存 legal incumbent。

只有当

$$
\boxed{
J_\lambda(\mathcal Q^{(t)})
>
J_\lambda(\mathcal P^{(t)})
}
$$

时才接受

$$
\mathcal P^{(t+1)}
=
\mathcal Q^{(t)}.
$$

否则保留原 incumbent：

$$
\mathcal P^{(t+1)}
=
\mathcal P^{(t)}.
$$

由于

$$
\eta_t
=
\frac{
T(\mathcal P^{(t)})
}{
\lambda m+(1-\lambda)P(\mathcal P^{(t)})
},
\qquad
\gamma_t=(1-\lambda)\eta_t,
$$

对于任意 candidate $\mathcal Q$，

$$
\boxed{
J_\lambda(\mathcal Q)
>
J_\lambda(\mathcal P^{(t)})
\iff
L_{\gamma_t}(\mathcal Q)
>
L_{\gamma_t}(\mathcal P^{(t)}).
}
$$

所以整个 epoch 可以共享同一个固定 $(\eta_t,\gamma_t)$。

只有接受新的 legal incumbent 后，才更新

$$
\boxed{
\eta_{t+1}
=
\frac{
T(\mathcal P^{(t+1)})
}{
\lambda m+(1-\lambda)P(\mathcal P^{(t+1)})
},
\qquad
\gamma_{t+1}=(1-\lambda)\eta_{t+1}.
}
$$

于是每个 epoch 为

$$
\boxed{
\text{Relax}
\rightarrow
\text{Project}
\rightarrow
\text{Refine}
\rightarrow
\text{Accept}
\rightarrow
\text{Update }\eta,\gamma.
}
$$

令

$$
\Delta_t
=
J_\lambda(\mathcal P^{(t+1)})-
J_\lambda(\mathcal P^{(t)}).
$$

搜索最多执行 `max_epochs` 个 epoch，并使用精确阈值
$\delta_{\min}=\texttt{min\_delta}$：

- $\Delta_t\le 0$ 时拒绝 candidate 并终止；
- $0<\Delta_t<\delta_{\min}$ 时接受 candidate，然后终止；
- $\Delta_t\ge\delta_{\min}$ 时接受并继续下一 epoch。

因此 `max_epochs` 给出硬上限，`min_delta` 给出统一的收益停止条件；不再需要区分 fixed-epoch 与 early-stop 两套 policy。

epoch search 结束后，从最终 legal incumbent 出发执行 Legal-only refinement。每个 Legal sweep 都重新建立当前 anchor、独立 accept/rollback，并使用同一个 $\delta_{\min}$ 判断是否继续。这样最终精修不依赖“是否恰好运行到预设最后一轮”，也不需要固定的 `legal_sweeps`。

由于只接受真实 $J_\lambda$ 改善，

$$
\boxed{
J_\lambda^{(t+1)}
\ge
J_\lambda^{(t)}.
}
$$

因此 legal incumbent 的真实 objective 单调不降。

这个设计的关键在于：

$$
\boxed{
\text{legal phase 中 root 可以暂时被固定，
但 relaxed phase 会周期性解除这种 pinning。}
}
$$

因此既不需要永久固定 root，也不需要显式求解昂贵的 root-subset optimization。

---

# 八、缓存、复杂度与实现结构

## 8.1 Node–Partition Connectivity Cache

定义

$$
\boxed{
c_v(S)
=
d(v,S)
=
|N(v)\cap S|.
}
$$

它表示节点 $v$ 与 partition $S$ 中真实 relation neighbors 的数量。

对于每个节点，只需要存储满足

$$
c_v(S)>0
$$

的 partitions。

因为每个这样的 partition 至少包含 $v$ 的一个 graph neighbor，

$$
\#\{S:c_v(S)>0\}
\le d(v).
$$

所以全图总非零项数满足

$$
\boxed{
\sum_v
\#\{S:c_v(S)>0\}
\le
\sum_v d(v)
=
2m.
}
$$

因此 sparse node–partition connectivity cache 的空间为

$$
\boxed{O(n+m).}
$$

此外，每个 active partition 只需保存

$$
n_S=|S|.
$$

legal phase 再额外保存

$$
r_S=\text{root of }S.
$$

所以 persistent optimization state 保持近线性规模。

---

## 8.2 Single-Node Move 的增量维护

若执行

$$
u:S_a\to S_b,
$$

只有 $u$ 的 graph neighbors 会看到 node–partition connectivity 改变。

对于

$$
v\in N(u),
$$

更新

$$
c_v(S_a)\mathrel{-}=1,
\qquad
c_v(S_b)\mathrel{+}=1.
$$

同时

$$
n_{S_a}\mathrel{-}=1,
\qquad
n_{S_b}\mathrel{+}=1.
$$

因此单次 relocation 的 persistent-cache update 成本为

$$
\boxed{O(d(u)).}
$$

同时可以直接利用当前 move 的

$$
\Delta T,\qquad \Delta P
$$

维护

$$
T\leftarrow T+\Delta T,
\qquad
P\leftarrow P+\Delta P.
$$

在 fixed-anchor FM pass 内无需每一步更新 $\gamma$。

---

## 8.3 Candidate Enumeration

对于 relaxed FM：

$$
\mathcal C_{\mathrm{relaxed}}(v)
=
\{S:c_v(S)>0\}
\cup
\{\varnothing\}.
$$

因此

$$
|\mathcal C_{\mathrm{relaxed}}(v)|
\le d(v)+1.
$$

全图一次 candidate sweep 为

$$
\boxed{O(n+m).}
$$

对于 legal FM，只需扫描 $N(v)$ 中的 active roots：

$$
\mathcal C_{\mathrm{legal}}(v)
=
\{
S_q:r_q\in N(v)
\}
\cup
\{\varnothing\},
$$

同样有

$$
|\mathcal C_{\mathrm{legal}}(v)|
\le d(v)+1,
$$

因此全图一次 legal candidate sweep 仍为

$$
\boxed{O(n+m).}
$$

所以 relaxed FM 与 legal FM 在数据结构上的区别很小：

$$
\boxed{
\begin{aligned}
\text{Relaxed:}\quad&
c_v(S)>0
\text{ 即可成为候选};\\
\text{Legal:}\quad&
r_S\in N(v)
\text{ 才能成为候选}.
\end{aligned}
}
$$

gain formula 与 persistent cache 完全共享。

---

## 8.4 FM Pass 的复杂度

如果一次 FM pass 中每个节点最多移动一次，则所有实际 move 的 adjacency update 总成本满足

$$
\sum_{v\text{ moved}}d(v)
\le
\sum_v d(v)
=
2m.
$$

因此纯 connectivity maintenance 为

$$
\boxed{O(m).}
$$

另外还需要：

- candidate evaluation；
- gain selection；
- priority queue / bucket maintenance；
- move locking；
- best-prefix bookkeeping。

如果使用 heap，pass 可以达到

$$
\boxed{O(m\log n)}
$$

量级。

若 gain management 使用高效 bucket 或 lazy priority mechanism，则实际成本可更接近

$$
\boxed{O(m).}
$$

因此目标是

$$
\boxed{
O(m)\text{-like per pass},
}
$$

而不是 $O(nk)$ 的 all-partition search。

---

## 8.5 Star Projection 的复杂度

对于 relaxed block $C$，节点 $v\in C$ 的 internal degree 为

$$
d(v,C)=c_v(C).
$$

因此扫描所有节点一次即可为每个 block 找到

$$
r_C^*
=
\arg\max_{v\in C}c_v(C).
$$

这一步为

$$
O(n).
$$

随后对每个选中的 root 扫描其 adjacency，以确定

$$
A^+(r_C^*)\cap C.
$$

每个 block 只选一个 root，因此总 root-adjacency scan 为 $O(m)$ 上界。

于是整个 projection 可以做到

$$
\boxed{O(n+m).}
$$

不需要：

- triangle enumeration；
- common-neighbor intersection；
- root-subset optimization；
- 二阶 topology cache。

---

## 8.6 统一的 Relocation Engine

实现上整个算法只需要一套 node relocation engine。

核心 gain 为

$$
\boxed{
g(v:p\to q)
=
c_v(S_q)
-
c_v(S_p)
-
\gamma(n_q-n_p+1).
}
$$

因为无自环，

$$
c_v(S_p)
=
d(v,S_p\setminus\{v\}),
$$

所以实现中无需特殊处理 source。

两种 FM mode 只改变 candidate-generation predicate：

$$
\operatorname{FM}
(
\mathcal P,
\gamma=(1-\lambda)\eta,
\operatorname{candidate\_predicate}
).
$$

relaxed mode：

$$
\operatorname{candidate\_predicate}(v,S)
=
[c_v(S)>0],
$$

legal mode：

$$
\operatorname{candidate\_predicate}(v,S)
=
[\{v,r_S\}\in E].
$$

因此 Relaxed FM 与 Legal FM 不需要两套优化器。

---

# 九、最终理论链条

整个方法可以概括为

$$
\boxed{
J_\lambda
\rightarrow
\eta=J_\lambda
\rightarrow
\gamma=(1-\lambda)\eta
\rightarrow
L_\gamma=T-\gamma P
\rightarrow
\text{exact node gain}
\rightarrow
\text{FM}.
}
$$

legal-star constraint 的核心结构不对称性是

$$
\boxed{
\text{leaf relocation cheap}
\qquad
\text{but}
\qquad
\text{root restructuring expensive}.
}
$$

因此不直接设计 root move，而采用

$$
\boxed{
\Omega_{\mathrm{legal}}
\rightarrow
\Omega_{\mathrm{relaxed}}
\rightarrow
\Omega_{\mathrm{legal}}.
}
$$

即

$$
\boxed{
\text{Relaxed CPM-FM}
\rightarrow
\text{Star Projection}
\rightarrow
\text{Legal FM}.
}
$$

其中：

$$
\boxed{
\text{Relaxed FM}
}
$$

负责解除 root pinning；

$$
\boxed{
\text{Star Projection}
}
$$

通过

$$
\arg\max_{v\in C}d(v,C)
$$

快速恢复 legal-star feasibility；

$$
\boxed{
\text{Legal FM}
}
$$

负责在新的 roots 下进行精细 leaf reassignment。

整个过程中，

$$
\boxed{
\eta
=
\frac{T}{\lambda m+(1-\lambda)P},
\qquad
\gamma
=
(1-\lambda)\eta.
}
$$

$\lambda$ 在整条 trajectory 中保持固定；$\eta$ 与 $\gamma$ 始终由当前 legal partition 重新计算。

初始化提供

$$
(\mathcal P_0,\eta_0,\gamma_0),
$$

FM pass 内固定 $(\eta,\gamma)$，pass 或 epoch 接受后重新计算。

最终算法为

$$
\boxed{
\text{Initialize}
\rightarrow
\text{Relax}
\rightarrow
\text{Project}
\rightarrow
\text{Refine}
\rightarrow
\text{Accept}
\rightarrow
\text{Update }\eta,\gamma,
}
$$

并通过始终保存 legal incumbent 保证

$$
\boxed{
J_\lambda^{(t+1)}
\ge
J_\lambda^{(t)}.
}
$$

因此，该方法用一次廉价的 constraint relaxation 暂时解除 root-induced search barrier，再通过 deterministic star projection 恢复 feasibility，并利用同一套 exact-gain FM engine 完成 constrained refinement，从而避免直接求解昂贵的 root restructuring，同时保持近线性的稀疏数据结构和可控的 per-pass complexity。
