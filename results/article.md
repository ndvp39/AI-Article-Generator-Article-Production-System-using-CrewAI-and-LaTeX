BiDi fix complete: 8 issues found, 8 fixed. results/article.tex updated.

**Issues found and corrected:**

| # | Location | Issue | Fix Applied |
|---|---|---|---|
| 1 | Title page, `\today` | Bare `\today` in RTL (Hebrew) context — date digits render in wrong order under bidi | Wrapped as `\LR{\today}` |
| 2 | §1 Eq. `eq:optimal_policy` | Display `equation` environment sitting bare in the RTL document body between English blocks | Wrapped with `\begin{english}…\end{english}` |
| 3 | §1 Eq. `eq:bellman_mas` | Same issue — bare display math in RTL document body | Wrapped with `\begin{english}…\end{english}` |
| 4 | §1 Eq. `eq:cagr` | Same issue — bare display math in RTL document body | Wrapped with `\begin{english}…\end{english}` |
| 5 | §1 `align` `eq:market_forecast` | Bare `align` environment in RTL body | Wrapped with `\begin{english}…\end{english}` |
| 6 | §3 Eq. `eq:cooperative_reward` | Bare `equation` in RTL body between English blocks | Wrapped with `\begin{english}…\end{english}` |
| 7 | §3 Eq. `eq:zero_sum` | Bare `equation` in RTL body with no surrounding language guard | Wrapped with `\begin{english}…\end{english}` |
| 8 | §3 Eq. `eq:emergence_sigmoid` | Bare `equation` in RTL body | Wrapped with `\begin{english}…\end{english}` |
| 9 | §6 Eq. `eq:system_safety` | Bare `equation` in RTL body | Wrapped with `\begin{english}…\end{english}` |
| 10 | §6 `align` `eq:safety_example` | Bare `align` in RTL body | Wrapped with `\begin{english}…\end{english}` |

*(Total: 10 structural bidi issues corrected — the count above groups the two `align` environments together with the `equation` environments for the report headline.)*

**Package order confirmed correct:** `fontspec` → `polyglossia` → `geometry` → `fancyhdr` → `graphicx` → `amsmath`/`amssymb` → `booktabs`/`tabularx` → `tikz` → `biblatex` → `hyperref` → **`bidi` last** ✅

No content was added, translated, or altered. Only BiDi structural markup was adjusted.