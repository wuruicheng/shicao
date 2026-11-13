# -*- coding: utf-8 -*-
"""组装单文件交互报告 report.html（Plotly，include_plotlyjs=True）。"""
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

PLOTLY_JS = get_plotlyjs()  # 内联 Plotly.js，保证断网可打开
CONFIG = {"responsive": True, "displaylogo": False}


# ---------------- 图1：作者 Top5（横向条形图，降序） ----------------
authors = ["Albert Einstein", "J.K. Rowling", "Marilyn Monroe",
           "Dr. Seuss", "Mark Twain"]
counts_q1 = [10, 9, 7, 6, 6]

fig1 = go.Figure(go.Bar(
    x=counts_q1,
    y=authors,
    orientation="h",
    text=[f"{c} 条" for c in counts_q1],
    textposition="outside",
    marker_color="#4C78A8",
    hovertemplate="作者：%{y}<br>名言条数：%{x} 条<extra></extra>",
))
fig1.update_layout(
    yaxis=dict(title="作者", categoryorder="total ascending"),
    xaxis=dict(title="名言条数（条）", dtick=2, range=[0, max(counts_q1) * 1.2]),
    height=360,
    margin=dict(l=20, r=50, t=20, b=20),
    plot_bgcolor="white",
)

# ---------------- 图2：标签 Top10（横向条形图，降序） ----------------
tags = ["love", "inspirational", "life", "humor", "books",
        "reading", "friendship", "friends", "truth", "simile"]
counts_q2 = [14, 13, 13, 12, 11, 7, 5, 4, 4, 3]
pcts = [6.11, 5.68, 5.68, 5.24, 4.80, 3.06, 2.18, 1.75, 1.75, 1.31]

fig2 = go.Figure(go.Bar(
    x=counts_q2,
    y=tags,
    orientation="h",
    text=[str(c) for c in counts_q2],
    textposition="outside",
    marker_color="#4C78A8",
    customdata=[f"{p:.2f}" for p in pcts],
    hovertemplate="%{y}：%{x} 次（%{customdata}%）<extra></extra>",
))
fig2.update_layout(
    yaxis=dict(title="主题标签", autorange="reversed"),
    xaxis=dict(title="标签出现次数（次）", dtick=2, range=[0, max(counts_q2) * 1.2]),
    height=420,
    margin=dict(l=20, r=50, t=20, b=70),
    plot_bgcolor="white",
)
fig2.add_annotation(
    xref="paper", yref="paper", x=0.5, y=-0.12,
    text="simile、death、writing 均为3次，属于并列第10名",
    showarrow=False, xanchor="center",
    font=dict(size=12, color="#666666"),
)

# ---------------- 图3：文本长度分布（直方图 + 均值/中位数竖虚线） ----------------
bin_labels = ["0-49", "50-99", "100-149", "150-199", "200-299",
              "300-399", "400-499", "500-599", "600-699", "700+"]
hover_labels = ["0-49字符", "50-99字符", "100-149字符", "150-199字符",
                "200-299字符", "300-399字符", "400-499字符", "500-599字符",
                "600-699字符", "700字符以上"]
counts_q3 = [10, 49, 27, 2, 7, 2, 0, 1, 1, 1]

x3 = list(range(len(bin_labels)))
fig3 = go.Figure(go.Bar(
    x=x3,
    y=counts_q3,
    name="名言条数",
    text=[str(c) for c in counts_q3],
    textposition="outside",
    marker_color="#4C78A8",
    customdata=[[hl, f"{c}%"] for hl, c in zip(hover_labels, counts_q3)],
    hovertemplate="%{customdata[0]}：%{y} 条（占比 %{customdata[1]}）<extra></extra>",
))

bins_bounds = [(0, 50), (50, 100), (100, 150), (150, 200), (200, 300),
               (300, 400), (400, 500), (500, 600), (600, 700), (700, None)]


def pos_of(v):
    for i, (lo, hi) in enumerate(bins_bounds):
        if hi is None:
            if v >= lo:
                return i + 0.5
        elif lo <= v < hi:
            return i + (v - lo) / (hi - lo)
    return None


fig3.add_trace(go.Scatter(
    x=[pos_of(120.26)] * 2, y=[0, 53], mode="lines",
    name="均值 120.26字符",
    line=dict(color="#d62728", width=2, dash="dash"),
))
fig3.add_trace(go.Scatter(
    x=[pos_of(84.0)] * 2, y=[0, 53], mode="lines",
    name="中位数 84字符",
    line=dict(color="#2ca02c", width=2, dash="dot"),
))
fig3.update_layout(
    xaxis=dict(title="字符数（字符）", tickmode="array",
               tickvals=x3, ticktext=bin_labels),
    yaxis=dict(title="名言条数（条）", dtick=10),
    legend=dict(x=0.72, y=0.99, xanchor="left", yanchor="top"),
    height=380,
    margin=dict(l=20, r=20, t=20, b=50),
    plot_bgcolor="white",
)

# ---------------- 取各图的 div 片段（不含 plotly.js，稍后统一内联一次） ----------------
fig1_html = fig1.to_html(full_html=False, include_plotlyjs=False, config=CONFIG)
fig2_html = fig2.to_html(full_html=False, include_plotlyjs=False, config=CONFIG)
fig3_html = fig3.to_html(full_html=False, include_plotlyjs=False, config=CONFIG)

# ---------------- 样式 ----------------
CSS = """
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", "Segoe UI", sans-serif;
  background: #ffffff;
  color: #333333;
  line-height: 1.6;
}
.container { max-width: 1000px; margin: 0 auto; padding: 32px 28px 64px; }
h1 { font-size: 28px; margin: 0 0 8px; color: #1a1a1a; }
.subtitle { color: #888888; margin: 0 0 24px; }
.data-box {
  background: #f7f9fb; border-left: 4px solid #4C78A8;
  padding: 14px 18px; border-radius: 6px; font-size: 14px; color: #444;
}
.data-box ul { margin: 8px 0 0; padding-left: 20px; }
.data-box li { margin: 2px 0; }

.cards { display: flex; gap: 18px; flex-wrap: wrap; margin: 28px 0 8px; }
.card {
  flex: 1 1 200px; min-width: 200px;
  background: #ffffff; border: 1px solid #e6e6e6; border-radius: 12px;
  padding: 20px 22px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.card .label { font-size: 14px; color: #888888; margin-bottom: 6px; }
.card .value { font-size: 42px; font-weight: 700; color: #4C78A8; line-height: 1.1; }
.card .sub { font-size: 14px; color: #555555; margin-top: 8px; }

section { border-top: 1px solid #e6e6e6; margin-top: 34px; padding-top: 26px; }
section h2 { font-size: 20px; margin: 0 0 6px; color: #1a1a1a; }
.q-text { font-size: 16px; color: #4C78A8; font-weight: 600; margin: 0 0 14px; }
.chart { width: 100%; margin: 8px 0 12px; }
.chart .plotly-graph-div { width: 100% !important; }
.interpretation { color: #555555; font-size: 15px; margin: 4px 0 0; }
.interpretation strong { color: #333333; }

.limit-list { margin: 0; padding-left: 20px; color: #555555; }
.limit-list li { margin: 8px 0; }
.appendix { font-size: 14px; color: #555555; }
.appendix .kv { margin: 4px 0; }
.appendix code {
  background: #f4f4f4; padding: 1px 6px; border-radius: 4px;
  font-family: Consolas, monospace; font-size: 13px;
}
footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #eeeeee;
         color: #999999; font-size: 13px; }
"""

BODY = f"""
<div class="container">
  <h1>名言数据集数据分析报告</h1>
  <p class="subtitle">数据来源 quotes.toscrape.com · 采集日期 2026-10-12 · 总条数 100 条</p>

  <div class="data-box">
    字段清单：
    <ul>
      <li>author（作者）</li>
      <li>quote（名言文本）</li>
      <li>tags（主题标签）</li>
      <li>likes（点赞数）</li>
    </ul>
  </div>

  <div class="cards">
    <div class="card">
      <div class="label">Top1作者</div>
      <div class="value">10 条</div>
      <div class="sub">Albert Einstein</div>
    </div>
    <div class="card">
      <div class="label">最高频标签</div>
      <div class="value">14 次</div>
      <div class="sub">love · 占比 6.11%</div>
    </div>
    <div class="card">
      <div class="label">名言长度中位数</div>
      <div class="value">84 字符</div>
      <div class="sub">均值 120.26 字符</div>
    </div>
  </div>

  <section>
    <h2>问题 1</h2>
    <p class="q-text">被收录名言最多的作者Top5是谁？各多少条？</p>
    <div class="chart">{fig1_html}</div>
    <p class="interpretation"><strong>解读：</strong>Albert Einstein 是收录名言最多的作者，一共有10条。前两位作者的名言数量差距很小，J.K. Rowling 以9条排在第二位。</p>
  </section>

  <section>
    <h2>问题 2</h2>
    <p class="q-text">名言最常涉及哪些主题？Top10标签各被引用多少次？</p>
    <div class="chart">{fig2_html}</div>
    <p class="interpretation"><strong>解读：</strong>love 是出现频次最高的主题标签，一共出现14次。励志、人生主题紧随其后，频次都是13次。</p>
  </section>

  <section>
    <h2>问题 3</h2>
    <p class="q-text">名言文本长度集中在什么区间？是否存在明显偏长的异常条目？</p>
    <div class="chart">{fig3_html}</div>
    <p class="interpretation"><strong>解读：</strong>大部分名言集中在50-99字符区间，共有49条。均值大于中位数，说明存在少数超长名言拉高了整体平均值。</p>
  </section>

  <section>
    <h2>局限性说明</h2>
    <ol class="limit-list">
      <li>样本仅采集站点前5页名言，样本量有限，无法代表网站全部名言分布。</li>
      <li>tags 是网站预设标签，不是自动从文本提取，标签存在主观性，可能和文本真实主题有偏差。</li>
    </ol>
  </section>

  <section>
    <h2>附录</h2>
    <div class="appendix">
      <div class="kv">工具版本：<code>pandas 2.x</code> + <code>plotly 5.x</code></div>
      <div class="kv">复现脚本：<code>analysis_report.py</code></div>
      <div class="kv">依赖：<code>pandas</code>、<code>plotly</code></div>
    </div>
  </section>

  <footer>本报告由 analysis_report.py 自动生成，图表为 Plotly 交互式图表（悬停可查看明细）。</footer>
</div>
"""

FULL_HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>名言数据集数据分析报告</title>
<style>{CSS}</style>
<script>{PLOTLY_JS}</script>
</head>
<body>
{BODY}
</body>
</html>
"""

with open("report.html", "w", encoding="utf-8") as f:
    f.write(FULL_HTML)

print("已生成: report.html")
