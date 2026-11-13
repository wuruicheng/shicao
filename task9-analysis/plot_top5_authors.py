# -*- coding: utf-8 -*-
"""生成「被收录名言最多的作者Top5」横向条形图（独立 HTML 文件）。"""
import plotly.graph_objects as go

# 已核对数据（按条数降序）
authors = ["Albert Einstein", "J.K. Rowling", "Marilyn Monroe",
           "Dr. Seuss", "Mark Twain"]
counts = [10, 9, 7, 6, 6]

fig = go.Figure(
    go.Bar(
        x=counts,
        y=authors,
        orientation="h",
        text=[f"{c} 条" for c in counts],      # 柱身数值标签
        textposition="outside",
        marker_color="#4C78A8",
        hovertemplate="作者：%{y}<br>名言条数：%{x} 条<extra></extra>",
    )
)

fig.update_layout(
    title=dict(
        text="被收录名言最多的作者Top5是谁？各多少条？",
        x=0.5,
        xanchor="center",
    ),
    xaxis=dict(
        title="名言条数（条）",
        dtick=2,
        range=[0, max(counts) * 1.2],
    ),
    yaxis=dict(
        title="作者",
        # 按数值升序排布：最小值在底部，最大值在顶部 => 从多到少、从上到下
        categoryorder="total ascending",
    ),
    margin=dict(l=20, r=40, t=60, b=20),
    plot_bgcolor="white",
)

fig.write_html("top5_authors_bar.html", include_plotlyjs=True)
print("已生成: top5_authors_bar.html")
