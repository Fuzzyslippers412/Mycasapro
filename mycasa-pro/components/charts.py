"""
Chart Components for MyCasa Pro
Premium visualizations with intentional design
"""
import streamlit as st
import plotly.graph_objects as go
from typing import List, Dict, Any
import pandas as pd


# Consistent color palette
COLORS = {
    "primary": "#6366F1",
    "secondary": "#818CF8", 
    "success": "#059669",
    "warning": "#D97706",
    "danger": "#DC2626",
    "info": "#0891B2",
    "text": "#1C1917",
    "text_secondary": "#57534E",
    "text_muted": "#A8A29E",
    "bg": "#FAFAF9",
    "surface": "#FFFFFF",
    "border": "#E7E5E4",
}

# Chart color sequence
CHART_COLORS = [
    "#6366F1",  # Indigo
    "#059669",  # Emerald  
    "#D97706",  # Amber
    "#0891B2",  # Cyan
    "#DC2626",  # Red
    "#7C3AED",  # Violet
    "#2563EB",  # Blue
    "#16A34A",  # Green
]


def _apply_light_theme(fig):
    """Apply consistent light theme to all charts"""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, -apple-system, sans-serif",
            color=COLORS["text_secondary"],
            size=12
        ),
        title=dict(
            font=dict(color=COLORS["text"], size=14, family="Inter"),
            x=0,
            xanchor="left"
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(size=11)
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        hoverlabel=dict(
            bgcolor=COLORS["surface"],
            bordercolor=COLORS["border"],
            font=dict(color=COLORS["text"], size=12)
        )
    )
    return fig


def portfolio_donut(holdings: List[Dict[str, Any]], title: str = "Portfolio Allocation"):
    """
    Portfolio allocation donut chart
    
    Intent: Visual breakdown of portfolio composition
    - Donut shows proportions at a glance
    - Center shows total value
    - Hover reveals exact amounts
    """
    if not holdings:
        st.info("No holdings data available")
        return
    
    df = pd.DataFrame(holdings)
    values = df.get('value', df.get('shares', []))
    total_value = sum(v for v in values if v) if any(values) else 0
    
    fig = go.Figure(data=[go.Pie(
        labels=df['ticker'],
        values=values,
        hole=0.65,
        marker=dict(
            colors=CHART_COLORS[:len(df)],
            line=dict(color=COLORS["surface"], width=2)
        ),
        textinfo='label+percent',
        textposition='outside',
        textfont=dict(size=11, color=COLORS["text_secondary"]),
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
        pull=[0.02] * len(df)  # Slight pull for visual separation
    )])
    
    # Center annotation
    fig.add_annotation(
        text=f"<b>${total_value/1000000:.2f}M</b><br><span style='font-size:10px;color:{COLORS['text_muted']}'>Total</span>",
        x=0.5, y=0.5,
        font=dict(size=18, color=COLORS["text"], family="JetBrains Mono"),
        showarrow=False
    )
    
    fig = _apply_light_theme(fig)
    fig.update_layout(
        showlegend=False,
        height=280,
        margin=dict(t=20, b=20, l=20, r=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def portfolio_performance_chart(holdings: List[Dict[str, Any]]):
    """
    Portfolio performance bar chart with daily changes
    
    Intent: Quick view of today's movers
    - Green/red bars for gain/loss
    - Sorted by performance for easy scanning
    """
    if not holdings:
        st.info("No holdings data")
        return
    
    df = pd.DataFrame(holdings)
    if 'change_pct' not in df.columns:
        st.info("No performance data available")
        return
    
    df = df.sort_values('change_pct', ascending=True)
    
    colors = [COLORS["success"] if x >= 0 else COLORS["danger"] for x in df['change_pct']]
    
    fig = go.Figure(go.Bar(
        x=df['change_pct'],
        y=df['ticker'],
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(width=0)
        ),
        text=[f"{x:+.2f}%" for x in df['change_pct']],
        textposition='outside',
        textfont=dict(size=11, color=COLORS["text_secondary"]),
        hovertemplate="<b>%{y}</b><br>Change: %{x:+.2f}%<extra></extra>"
    ))
    
    fig = _apply_light_theme(fig)
    fig.update_layout(
        height=max(200, len(df) * 35),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor=COLORS["border"],
            zeroline=True,
            zerolinecolor=COLORS["text_muted"],
            zerolinewidth=1,
            ticksuffix="%"
        ),
        yaxis=dict(
            title="",
            showgrid=False
        ),
        margin=dict(l=60, r=60, t=20, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def holdings_value_chart(holdings: List[Dict[str, Any]]):
    """
    Treemap of portfolio holdings by value
    
    Intent: Visual representation of portfolio weight
    - Larger boxes = larger positions
    - Color indicates asset type
    """
    if not holdings:
        return
    
    df = pd.DataFrame(holdings)
    if 'value' not in df.columns or not any(df['value']):
        return
    
    fig = go.Figure(go.Treemap(
        labels=df['ticker'],
        parents=[""] * len(df),
        values=df['value'],
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>$%{value:,.0f}",
        marker=dict(
            colors=CHART_COLORS[:len(df)],
            line=dict(width=2, color=COLORS["surface"])
        ),
        hovertemplate="<b>%{label}</b><br>Value: $%{value:,.0f}<br>%{percentRoot:.1%} of portfolio<extra></extra>"
    ))
    
    fig = _apply_light_theme(fig)
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def budget_bars(budget_data: List[Dict[str, Any]]):
    """
    Budget vs spending horizontal bars
    
    Intent: Clear budget utilization view
    - Shows spent vs limit
    - Color indicates if over/under budget
    """
    if not budget_data:
        st.info("No budget data available")
        return
    
    df = pd.DataFrame(budget_data)
    
    fig = go.Figure()
    
    # Budget limit (background)
    fig.add_trace(go.Bar(
        y=df['category'],
        x=df['limit'],
        orientation='h',
        name='Budget',
        marker=dict(color=COLORS["border"]),
        hovertemplate="Budget: $%{x:,.0f}<extra></extra>"
    ))
    
    # Spent (foreground)
    colors = [COLORS["danger"] if s > l else COLORS["success"] 
              for s, l in zip(df['spent'], df['limit'])]
    
    fig.add_trace(go.Bar(
        y=df['category'],
        x=df['spent'],
        orientation='h',
        name='Spent',
        marker=dict(color=colors),
        text=[f"${s:,.0f}" for s in df['spent']],
        textposition='inside',
        textfont=dict(color="white", size=11),
        hovertemplate="Spent: $%{x:,.0f}<extra></extra>"
    ))
    
    fig = _apply_light_theme(fig)
    fig.update_layout(
        barmode='overlay',
        height=max(150, len(df) * 40),
        showlegend=False,
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor=COLORS["border"],
            tickprefix="$"
        ),
        yaxis=dict(title="", showgrid=False),
        margin=dict(l=100, r=20, t=20, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def spending_trend(transactions: List[Dict[str, Any]], days: int = 30):
    """
    Cumulative spending trend over time
    
    Intent: Track spending trajectory
    - Area chart shows cumulative spend
    - Helps identify spending patterns
    """
    if not transactions:
        st.info("No transaction data")
        return
    
    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['date'])
    
    # Daily totals
    daily = df.groupby(df['date'].dt.date)['amount'].sum().reset_index()
    daily.columns = ['date', 'amount']
    daily['cumulative'] = daily['amount'].cumsum()
    
    fig = go.Figure()
    
    # Area fill
    fig.add_trace(go.Scatter(
        x=daily['date'],
        y=daily['cumulative'],
        mode='lines',
        fill='tozeroy',
        line=dict(color=COLORS["primary"], width=2),
        fillcolor=f"rgba(99, 102, 241, 0.1)",
        hovertemplate="<b>%{x}</b><br>Total: $%{y:,.0f}<extra></extra>"
    ))
    
    # Markers on data points
    fig.add_trace(go.Scatter(
        x=daily['date'],
        y=daily['cumulative'],
        mode='markers',
        marker=dict(color=COLORS["primary"], size=6),
        hoverinfo='skip'
    ))
    
    fig = _apply_light_theme(fig)
    fig.update_layout(
        height=220,
        showlegend=False,
        xaxis=dict(
            title="",
            showgrid=False,
            tickformat="%b %d"
        ),
        yaxis=dict(
            title="",
            showgrid=True,
            gridcolor=COLORS["border"],
            tickprefix="$"
        ),
        margin=dict(l=50, r=20, t=20, b=30)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def task_timeline(tasks: List[Dict[str, Any]]):
    """
    Task timeline visualization
    
    Intent: Visual task schedule
    - Shows tasks on a calendar timeline
    - Priority indicated by color
    """
    if not tasks:
        st.info("No scheduled tasks")
        return
    
    dated_tasks = [t for t in tasks if t.get('scheduled_date') or t.get('due_date')]
    if not dated_tasks:
        st.info("No tasks with dates")
        return
    
    df = pd.DataFrame(dated_tasks)
    df['date'] = pd.to_datetime(df.get('scheduled_date', df.get('due_date')))
    
    priority_colors = {
        "urgent": COLORS["danger"],
        "high": COLORS["warning"],
        "medium": COLORS["primary"],
        "low": COLORS["success"]
    }
    
    fig = go.Figure()
    
    for _, row in df.iterrows():
        color = priority_colors.get(row['priority'], COLORS["primary"])
        fig.add_trace(go.Scatter(
            x=[row['date']],
            y=[row.get('category', 'General')],
            mode='markers+text',
            marker=dict(size=12, color=color, symbol='circle'),
            text=[row['title'][:15] + '...' if len(row['title']) > 15 else row['title']],
            textposition='top center',
            textfont=dict(size=10, color=COLORS["text_secondary"]),
            hovertemplate=f"<b>{row['title']}</b><br>Priority: {row['priority']}<br>%{{x}}<extra></extra>"
        ))
    
    fig = _apply_light_theme(fig)
    fig.update_layout(
        showlegend=False,
        height=180,
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor=COLORS["border"],
            tickformat="%b %d"
        ),
        yaxis=dict(title="", showgrid=False),
        margin=dict(l=80, r=20, t=30, b=30)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def holdings_table(holdings: List[Dict[str, Any]]):
    """
    Interactive holdings table
    
    Intent: Detailed holdings view with all metrics
    - Sortable columns
    - Formatted numbers
    - Change indicators
    """
    if not holdings:
        st.info("No holdings data")
        return
    
    df = pd.DataFrame(holdings)
    
    # Format columns for display
    display_df = df.copy()
    
    if 'value' in display_df.columns:
        display_df['Value'] = display_df['value'].apply(lambda x: f"${x:,.0f}" if x else "—")
    if 'price' in display_df.columns:
        display_df['Price'] = display_df['price'].apply(lambda x: f"${x:,.2f}" if x else "—")
    if 'change_pct' in display_df.columns:
        display_df['Today'] = display_df['change_pct'].apply(
            lambda x: f"{'🟢' if x >= 0 else '🔴'} {x:+.2f}%" if x is not None else "—"
        )
    if 'shares' in display_df.columns:
        display_df['Shares'] = display_df['shares'].apply(lambda x: f"{x:,.2f}" if x else "—")
    
    # Select and rename columns
    columns = {
        'ticker': 'Ticker',
        'type': 'Type',
        'Shares': 'Shares',
        'Price': 'Price',
        'Value': 'Value',
        'Today': 'Today'
    }
    
    final_cols = [c for c in columns.keys() if c in display_df.columns or columns[c] in display_df.columns]
    rename_map = {k: v for k, v in columns.items() if k in display_df.columns}
    
    display_df = display_df.rename(columns=rename_map)
    final_display_cols = [columns.get(c, c) for c in final_cols]
    
    st.dataframe(
        display_df[[c for c in final_display_cols if c in display_df.columns]],
        use_container_width=True,
        hide_index=True,
        height=min(400, len(display_df) * 38 + 38)
    )
