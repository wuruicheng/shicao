# -*- coding: utf-8 -*-
"""生成「名言文本长度分布」柱状图（show_q3.html）。"""
import plotly.graph_objects as go

# 已核对的分箱结果（左闭右开，不重新计算）
bin_labels = ["0-49", "50-99", "100-149", "150-199", "200-299",
              "300-399", "400-499", "500-599", "600-699", "700+"]
hover_labels = ["0-49字符", "50-99字符", "100-149字符", "150-199字符",
                "200-299字符", "300-399字符", "400-499字符", "500-599字符",
                "600-699字符", "700字符以上"]
counts = [10, 49, 27, 2, 7, 2, 0, 1, 1, 1]
total = 100

mean = 120.26
median = 84.0

# 柱子 x 用序号 0..9，再用 ticktext 映射成区间标签（保持区间顺序，不按数值排序）
x = list(range(len(bin_labels)))

fig = go.Figure(
    go.Bar(
        x=x,
        y=counts,
        name="名言条数",
        text=[str(c) for c in counts],      # 柱身显示条数
        textposition="outside",
        marker_color="#4C78A8",
        customdata=[[hl, f"{c}%"] for hl, c in zip(hover_labels, counts)],
        hovertemplate="%{customdata[0]}：%{y} 条（占比 %{customdata[1]}）<extra></extra>",
    )
)

# 把具体字符数映射到类别轴上的位置，用于画均值/中位数竖虚线
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


pos_mean = pos_of(mean)
pos_median = pos_of(median)

fig.add_trace(go.Scatter(
    x=[pos_mean, pos_mean], y=[0, 53], mode="lines",
    name="均值 120.26字符",
    line=dict(color="#d62728", width=2, dash="dash"),
))
fig.add_trace(go.Scatter(
    x=[pos_median, pos_median], y=[0, 53], mode="lines",
    name="中位数 84字符",
    line=dict(color="#2ca02c", width=2, dash="dot"),
))

fig.update_layout(
    title=dict(
        text="名言文本长度集中在什么区间？是否存在明显偏长的异常条目？",
        x=0.5,
        xanchor="center",
    ),
    xaxis=dict(
        title="字符数（字符）",
        tickmode="array",
        tickvals=x,
        ticktext=bin_labels,
    ),
    yaxis=dict(title="名言条数（条）", dtick=10),
    legend=dict(x=0.72, y=0.99, xanchor="left", yanchor="top"),
    margin=dict(l=20, r=20, t=70, b=50),
    plot_bgcolor="white",
)

fig.write_html("show_q3.html", include_plotlyjs=True)
print("已生成: show_q3.html")
