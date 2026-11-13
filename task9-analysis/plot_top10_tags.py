# -*- coding: utf-8 -*-
"""生成「名言最常涉及的主题 Top10 标签」横向条形图（show_q2.html）。"""
import plotly.graph_objects as go

# 已核对数据（按次数降序，不重新计算）
tags = ["love", "inspirational", "life", "humor", "books",
        "reading", "friendship", "friends", "truth", "simile"]
counts = [14, 13, 13, 12, 11, 7, 5, 4, 4, 3]
pcts = [6.11, 5.68, 5.68, 5.24, 4.80, 3.06, 2.18, 1.75, 1.75, 1.31]

fig = go.Figure(
    go.Bar(
        x=counts,
        y=tags,
        orientation="h",
        text=[str(c) for c in counts],      # 柱身显示次数
        textposition="outside",
        marker_color="#4C78A8",
        customdata=[f"{p:.2f}" for p in pcts],
        hovertemplate="%{y}：%{x} 次（%{customdata}%）<extra></extra>",
    )
)

fig.update_layout(
    title=dict(
        text="名言最常涉及哪些主题？Top10标签各被引用多少次？",
        x=0.5,
        xanchor="center",
    ),
    xaxis=dict(
        title="标签出现次数（次）",
        dtick=2,
        range=[0, max(counts) * 1.2],
    ),
    yaxis=dict(
        title="主题标签",
        autorange="reversed",   # 反转 y 轴 => 数据首项(love, 14)在最上方
    ),
    margin=dict(l=20, r=40, t=70, b=90),
    plot_bgcolor="white",
)

# 图下方注释：并列第10名说明
fig.add_annotation(
    xref="paper", yref="paper",
    x=0.5, y=-0.12,
    text="simile、death、writing 均为3次，属并列第10名",
    showarrow=False,
    xanchor="center",
    font=dict(size=12, color="#666666"),
)

fig.write_html("show_q2.html", include_plotlyjs=True)
print("已生成: show_q2.html")
