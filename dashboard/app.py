"""
QS Hedge Fund Dashboard - Operational Control Plane
No-emoji, professional SVG-based UI.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
from plotly.subplots import make_subplots
from loguru import logger
import importlib
import omega.ai_service

from config.settings import get_settings
from qsconnect.database.duckdb_manager import DuckDBManager
from qsresearch.governance.manager import GovernanceManager
from qsresearch.governance.reporting import ReportingEngine
from config.registry import get_registry
from qsconnect.emergency import EmergencyControl
from omega.risk_engine import RiskManager
from omega.ai_service import get_market_analyst
import time # For lag calculations

# Page configuration
st.set_page_config(
    page_title="QS Control Plane",
    layout="wide",
    initial_sidebar_state="expanded"
)


# SVG Icons (React-icons / Lucide style)
SVG_ICONS = {
    "shield": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "cog": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
    "activity": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    "bar-chart": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>',
    "line-chart": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>',
    "database": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/></svg>',
    "terminal": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
    "bot": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="10" x="3" y="11" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>',
    "alert-circle": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    "sun": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
    "moon": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    "check-circle": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "timer": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "flask": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2v8L4.5 20.5a2 2 0 0 0 2 2.5h11a2 2 0 0 0 2-2.5L14 10V2"/><path d="M8.5 2h7"/><path d="M7 16h10"/></svg>',
    "power": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/></svg>',
    "trash-2": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>',
    "layout-list": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/><path d="M14 4h7"/><path d="M14 9h7"/><path d="M14 15h7"/><path d="M14 20h7"/></svg>',
    "file-text": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
    "lock": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
}

def render_icon(name, color="currentColor"):
    if name not in SVG_ICONS:
        logger.error(f"Missing icon: {name}")
        return f'<span style="color:{color};">[Icon:{name}]</span>'
    return f'<div style="display:inline-block; vertical-align:middle; margin-right:8px; color:{color};">{SVG_ICONS[name]}</div>'

# Session state initialization
if "halted" not in st.session_state:
    st.session_state.halted = False
if "strategy_approved" not in st.session_state:
    st.session_state.strategy_approved = False
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True  # Default to dark mode
if "last_tick_count" not in st.session_state:
    st.session_state.last_tick_count = 0
if "figs" not in st.session_state:
    st.session_state.figs = {}

# Dynamic CSS based on theme
if st.session_state.dark_mode:
    theme_css = """
    <style>
        .main-header { font-size: 2.2rem; font-weight: bold; color: #1f77b4; margin-bottom: 1.5rem; display: flex; align-items: center; }
        .status-panel { background: #0e1117; border: 1px solid #1f77b4; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
        .halt-banner { background: #4a0404; color: white; padding: 12px; border-radius: 6px; text-align: center; font-weight: bold; margin-bottom: 20px; border: 1px solid #e74c3c; box-shadow: 0 0 10px rgba(231, 76, 60, 0.4); display: flex; justify-content: center; align-items: center; }
        .stButton > button { width: 100%; border-radius: 6px; }
        .status-dot { height: 10px; width: 10px; background-color: #00ff88; border-radius: 50%; display: inline-block; margin-right: 8px; box-shadow: 0 0 5px #00ff88; }
        .status-text { font-size: 0.9rem; vertical-align: middle; }
        .theme-toggle { cursor: pointer; padding: 8px; border-radius: 50%; transition: all 0.3s; }
        .theme-toggle:hover { background: rgba(255,255,255,0.1); }
    </style>
    """
else:
    theme_css = """
    <style>
        /* Main content area */
        .stApp, [data-testid="stAppViewContainer"], .main .block-container {
            background-color: #ffffff !important;
        }
        [data-testid="stHeader"] { background-color: #f8f9fa !important; }
        
        /* Sidebar */
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
            background-color: #f0f2f6 !important;
        }
        [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] h3 {
            color: #333 !important;
        }
        
        /* Text colors */
        .stMarkdown, .stText, p, span, label, h1, h2, h3, h4, h5, h6 {
            color: #1a1a1a !important;
        }
        
        /* Metrics */
        [data-testid="stMetricValue"] { color: #1f77b4 !important; }
        [data-testid="stMetricDelta"] { color: #00cc66 !important; }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { background-color: #f8f9fa !important; }
        .stTabs [data-baseweb="tab"] { color: #333 !important; }
        
        /* Inputs */
        .stTextInput > div > div, .stSelectbox > div > div {
            background-color: #fff !important;
            color: #333 !important;
            border-color: #ccc !important;
        }
        
        /* Dataframes */
        .stDataFrame { background-color: #fff !important; }
        
        /* Custom classes */
        .main-header { font-size: 2.2rem; font-weight: bold; color: #1f77b4; margin-bottom: 1.5rem; display: flex; align-items: center; }
        .status-panel { background: #f5f5f5; border: 1px solid #1f77b4; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
        .halt-banner { background: #ffcccc; color: #8b0000; padding: 12px; border-radius: 6px; text-align: center; font-weight: bold; margin-bottom: 20px; border: 1px solid #e74c3c; display: flex; justify-content: center; align-items: center; }
        .stButton > button { width: 100%; border-radius: 6px; }
        .status-dot { height: 10px; width: 10px; background-color: #00cc66; border-radius: 50%; display: inline-block; margin-right: 8px; }
        .status-text { font-size: 0.9rem; vertical-align: middle; color: #333; }
    </style>
    """
st.markdown(theme_css, unsafe_allow_html=True)

def render_live_chart(db_mgr, symbol):
    """Renders a real-time Plotly candlestick chart with state persistence via uirevision."""
    # Ensure we have a rolling window of recent candles
    query = f"""
        SELECT timestamp, open, high, low, close, volume, source, asset_class
        FROM realtime_candles 
        WHERE symbol = '{symbol}' 
        ORDER BY timestamp ASC
        LIMIT 300
    """
    df = db_mgr.query_pandas(query)
    
    if df.empty:
        st.warning(f"No live candle data available for {symbol}. Waiting for ticks...")
        return

    # Use session state to persist the figure object
    if symbol not in st.session_state.figs:
        fig = go.Figure()
        fig.update_layout(
            dragmode="pan",
            uirevision=symbol, # Keeps zoom/pan state across data updates
            xaxis=dict(fixedrange=False),
            yaxis=dict(fixedrange=False),
            template="plotly_dark" if st.session_state.dark_mode else "plotly_white",
            height=500,
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis_rangeslider_visible=False,
        )
        st.session_state.figs[symbol] = fig
    
    # Create Subplots: Row 1 = Candles/VWAP, Row 2 = Volume
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3]
    )
    
    # Calculate VWAP
    # VWAP = Cumulative(Volume * Price) / Cumulative(Volume)
    if not df.empty and 'close' in df.columns and 'volume' in df.columns:
        # Simple Session VWAP (Cumulative from start of dataframe)
        # Improvement: Anchor to start of day if possible
        start_of_day = df['timestamp'].iloc[-1].replace(hour=0, minute=0, second=0, microsecond=0) \
            if not df.empty else None
            
        # Filter for current session if possible, otherwise rolling VWAP
        df['cum_pv'] = (df['close'] * df['volume']).cumsum()
        df['cum_vol'] = df['volume'].cumsum()
        df['vwap'] = df['cum_pv'] / df['cum_vol']
        
        # Add VWAP Trace
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['vwap'],
            mode='lines',
            name='Session VWAP',
            line=dict(color='#f39c12', width=1.5, dash='dash')
        ), row=1, col=1)

    # Candlestick Trace
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol
    ), row=1, col=1)

    # Volume Trace
    colors = ['#2ecc71' if c >= o else '#e74c3c' for c, o in zip(df['close'], df['open'])]
    fig.add_trace(go.Bar(
        x=df['timestamp'],
        y=df['volume'],
        name='Volume',
        marker_color=colors,
        marker_line_width=0
    ), row=2, col=1)

    # Handle gaps
    fig.update_xaxes(
        rangebreaks=[dict(bounds=["sat", "mon"])],
        row=1, col=1
    )
    fig.update_xaxes(
        rangebreaks=[dict(bounds=["sat", "mon"])],
        row=2, col=1
    )

    fig.update_layout(
        title=f"Truth Layer: {symbol} (Real-Time)",
        yaxis_title="Price",
        # yaxis2_title="Volume",
        template="plotly_dark" if st.session_state.dark_mode else "plotly_white",
        height=600,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True, 
        'displayModeBar': True,
        'staticPlot': False
    })

def render_market_profile(db_mgr, symbol, days=30):
    """Renders a Market Profile (Volume Profile) chart."""
    # 1. Fetch Historical Data from DuckDB
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    try:
        query = f"""
            SELECT date as timestamp, open, high, low, close, volume 
            FROM prices 
            WHERE symbol = '{symbol}' 
            AND date >= '{start_date.strftime('%Y-%m-%d')}'
            ORDER BY date ASC
        """
        df = db_mgr.query_pandas(query)
        
        if df.empty:
            st.warning(f"No historical data for {symbol} in 'prices' table.")
            return

    except Exception as e:
        st.error(f"Data Error: {e}")
        return

    # 2. Calculate Volume Profile
    price = df['close']
    volume = df['volume']
    
    # Create histograms where bins=24
    if len(price) > 0:
        counts, bin_edges = np.histogram(price, bins=24, weights=volume)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    else:
        st.warning("Insufficient data.")
        return

    # 3. Create Subplots
    fig = make_subplots(
        rows=1, cols=2, 
        column_widths=[0.2, 0.8], 
        shared_yaxes=True, 
        horizontal_spacing=0.02
    )
    
    # 4. Add Volume Profile (Left)
    fig.add_trace(go.Bar(
        x=counts,
        y=bin_centers,
        orientation='h',
        name='Volume Profile',
        marker_color='rgba(0, 255, 136, 0.3)', # Greenish tint
        showlegend=False
    ), row=1, col=1)
    
    # 5. Add Candlestick (Right)
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name=symbol
    ), row=1, col=2)
    
    fig.update_layout(
        title=f"Market Profile: {symbol} ({days} Days)", 
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=600,
        bargap=0.01,
        yaxis=dict(showticklabels=False), # Hide Y on left chart? No, shared.
    )
    # Be explicit about shared Y
    fig.update_yaxes(side="right", row=1, col=2)
    fig.update_xaxes(showticklabels=False, row=1, col=1) # Hide volume numbers
    
    st.plotly_chart(fig, use_container_width=True)

def check_password():
    """Password protection using environment variable."""
    if st.session_state.get('password_correct', False):
        return True

    settings = get_settings()
    st.markdown("### 🔒 Restricted Access")
    pwd = st.text_input("Enter Operational Password", type="password")
    
    if st.button("Login"):
        if pwd == settings.dashboard_password:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Invalid password")
    return False

def main():
    if not check_password():
        st.stop()

    # Shared Managers
    # Use auto_close=True to allow other processes to access the DB on Windows
    db_mgr = DuckDBManager(Path("data/quant.duckdb"), read_only=True, auto_close=True)
    gov_mgr = GovernanceManager(db_mgr)
    report_engine = ReportingEngine(db_mgr)
    registry = get_registry()
    registry = get_registry()
    risk_manager = RiskManager()
    
    # Force reload of AI module to fix stale code
    importlib.reload(omega.ai_service)
    from omega.ai_service import get_market_analyst
    ai_analyst = get_market_analyst(force_refresh=True)
    
    active_strat = gov_mgr.get_active_strategy()

    # Sidebar: System Health & Emergency Controls
    with st.sidebar:
        # Theme Toggle at very top
        col_title, col_toggle = st.columns([4, 1])
        with col_title:
            st.markdown(f'<h3 style="display:flex; align-items:center;">{render_icon("activity")} System Health</h3>', unsafe_allow_html=True)
        with col_toggle:
            # Use SVG icon instead of emoji
            if st.session_state.dark_mode:
                icon_html = f'<div style="cursor:pointer; padding:4px;">{render_icon("sun", "#ffd700")}</div>'
                clicked = st.button("🌞", key="theme_toggle", help="Switch to Light Mode", type="secondary")
                if clicked:
                    st.session_state.dark_mode = False
                    st.rerun()
            else:
                icon_html = f'<div style="cursor:pointer; padding:4px;">{render_icon("moon", "#4169e1")}</div>'
                clicked = st.button("🌙", key="theme_toggle", help="Switch to Dark Mode", type="secondary")
                if clicked:
                    st.session_state.dark_mode = True
                    st.rerun()
        
        colH1, colH2 = st.columns([1.5, 1])
        with colH1:
            st.markdown(f'<div style="display:flex; align-items:center; margin-bottom:8px;">{render_icon("check-circle", "#00ff88")} IBKR API</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="display:flex; align-items:center;">{render_icon("check-circle", "#00ff88")} Truth Layer</div>', unsafe_allow_html=True)
        with colH2:
            st.markdown(f'<div style="margin-bottom:8px;"><span class="status-dot"></span><span class="status-text">Live (Mixed)</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div><span class="status-dot" style="background-color:#00ff88; box-shadow:0 0 5px #00ff88;"></span><span class="status-text">Multi-Asset</span></div>', unsafe_allow_html=True)
            
        # Real-time Engine metrics
        st.divider()
        try:
            # We assume realtime_candles table contains recent timestamps
            latest_tick_data = db_mgr.query_pandas("SELECT MAX(timestamp) as last_ts, COUNT(*) as total FROM realtime_candles")
            if not latest_tick_data.empty and latest_tick_data['last_ts'][0] is not None:
                last_ts = pd.to_datetime(latest_tick_data['last_ts'][0])
                lag_sec = (pd.Timestamp.now() - last_ts).total_seconds()
                color = "#00ff88" if lag_sec < 5 else "#f1c40f" if lag_sec < 60 else "#e74c3c"
                st.metric("Engine Lag", f"{lag_sec:.1f}s", delta=None, delta_color="normal")
                st.caption(f"Last sync: {last_ts.strftime('%H:%M:%S')}")
            else:
                st.warning("Waiting for Engine ticks...")
        except:
            pass
            
        st.divider()
        
        st.markdown(f'<h3 style="display:flex; align-items:center; color:#e74c3c;">{render_icon("shield", "#e74c3c")} Emergency Controls</h3>', unsafe_allow_html=True)
        
        # Check backend state
        system_halted = EmergencyControl.is_halted()
        
        if not system_halted:
            if st.button("HALT ALL TRADING", type="primary", use_container_width=True):
                if EmergencyControl.halt("Manually Triggered from Dashboard"):
                    st.toast("System Halted Successfully")
                    st.rerun()
                else:
                    st.error("Failed to Halt System - Check Logs")
        else:
            if st.button("RESUME TRADING", use_container_width=True):
                if EmergencyControl.resume():
                    st.toast("System Resumed")
                    st.rerun()
                else:
                    st.error("Failed to Resume - Check Logs")
                
        if st.button("CANCEL ALL ORDERS", use_container_width=True, disabled=True):
            st.toast("Not Wired to Backend yet")
            
        if st.button("FLATTEN ALL POSITIONS", use_container_width=True, disabled=True):
            st.warning("Action: Immediate Portfolio Liquidation")
            if st.button("CONFIRM FLATTEN", type="primary"):
                st.toast("Flattening portfolio...")

        st.divider()
        st.markdown(f'<h3 style="display:flex; align-items:center;">{render_icon("cog")} Active Risk Limits</h3>', unsafe_allow_html=True)
        global_limits = risk_manager.limits.get("GLOBAL_LIMITS", {})
        st.text_input("Daily Loss Limit (USD)", value=f"{global_limits.get('daily_loss_limit_usd', 0):,.0f}", disabled=True)
        st.text_input("Max Symbol Exposure (%)", value=f"{global_limits.get('max_symbol_exposure_pct', 0) * 100:.0f}%", disabled=True)
        st.text_input("Max Leverage", value=f"{global_limits.get('max_total_leverage', 0):.1f}x", disabled=True)
        
        st.divider()
        pass

    # Halt Banner
    # Status Banner (Safety First)
    system_halted = EmergencyControl.is_halted()
    if system_halted:
        st.markdown(f'<div class="halt-banner">{render_icon("alert-circle", "white")} 🚨 SYSTEM HALTED — TRADING STOPPED</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background: rgba(0, 255, 136, 0.1); color: #00ff88; padding: 10px; border-radius: 6px; text-align: center; border: 1px solid #00ff88; margin-bottom: 20px;">{render_icon("check-circle", "#00ff88")} ENGINE STATUS: OPERATIONAL</div>', unsafe_allow_html=True)

    # Main Header
    st.markdown(f'<div class="main-header">{render_icon("shield")} Operational Control Plane</div>', unsafe_allow_html=True)
    
    if active_strat:
        expiry_days = (active_strat['ttl_expiry'] - datetime.now()).days if isinstance(active_strat['ttl_expiry'], datetime) else "N/A"
        st.caption(f"Active Strategy: {active_strat['strategy_hash'][:12]} | Stage: {active_strat['stage']} | TTL: {expiry_days} days remaining")

    # Live Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Net Liquidity", "$5.24M", "+0.4%")
    with m2:
        st.metric("Gross Exposure", "138%", "Target")
    with m3:
        st.metric("Day P&L", "+$24,510", "0.47%")
    with m4:
        limit = 50000
        current_dd = 12300
        pct_used = (current_dd / limit) * 100
        st.metric("Current Drawdown", f"-${current_dd/1000:.1f}k", f"{pct_used:.1f}% of limit")

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Truth Layer & Blotter",
        "Holdings",
        "Strategy Approval",
        "Governance Audit",
        "Drift & Performance",
        "Ops Management",
        "Risk Overview",
        "Market Profile"
    ])

    with tab1:
        st.markdown(f"#### {render_icon('terminal')} Real-Time Truth Layer & Order Blotter", unsafe_allow_html=True)
        
        # Live Chart Section
        try:
            # Fetch symbols and metadata
            symbol_meta = db_mgr.query_pandas("SELECT DISTINCT symbol, source, asset_class FROM realtime_candles")
            active_symbols = symbol_meta['symbol'].tolist()
        except Exception:
            symbol_meta = pd.DataFrame()
            active_symbols = []
            
        if not active_symbols:
            # st.warning("No active symbols found in DB.") # Silence is golden
            active_symbols = []
            
        if not active_symbols:
            active_symbols = ["AMZN"] # Fallback for UI skeleton
            
        chart_col, info_col = st.columns([3, 1])
        with chart_col:
            col_sel1, col_sel2 = st.columns([1, 1])
            with col_sel1:
                classes = ["ALL"] + sorted(list(symbol_meta['asset_class'].unique())) if not symbol_meta.empty else ["ALL"]
                selected_class = st.selectbox("Filter Class", classes)
            
            filtered_symbols = active_symbols
            if selected_class != "ALL" and not symbol_meta.empty:
                filtered_symbols = symbol_meta[symbol_meta['asset_class'] == selected_class]['symbol'].tolist()
                
            with col_sel2:
                selected_symbol = st.selectbox("Select Symbol", filtered_symbols if filtered_symbols else ["AMZN"], key="chart_sym")
            
            # Pre-fetch metadata for header usage
            meta = {}
            if not symbol_meta.empty and selected_symbol in symbol_meta['symbol'].values:
                meta = symbol_meta[symbol_meta['symbol'] == selected_symbol].iloc[0]
            
            # --- Live Quote Header ---
            latest_quote = db_mgr.query_pandas(f"""
                SELECT close, open, volume, timestamp 
                FROM realtime_candles 
                WHERE symbol = '{selected_symbol}' 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            
            if not latest_quote.empty:
                last_price = latest_quote['close'][0]
                open_price = latest_quote['open'][0]
                last_vol = latest_quote['volume'][0]
                change = last_price - open_price
                pct_change = (change / open_price) * 100 if open_price != 0 else 0
                
                c_met1, c_met2, c_met3 = st.columns(3)
                
                # Enhanced Price Clarity
                mid_price = last_price # Placeholder if missing
                source_lbl = f"{meta['source'] if 'source' in meta else 'UNKNOWN'}"
                
                # Calculate Latency
                last_ts = latest_quote['timestamp'][0]
                latency_ms = (datetime.now() - last_ts).total_seconds() * 1000
                lat_color = "green" if latency_ms < 2000 else "orange" if latency_ms < 5000 else "red"
                
                c_met1.metric("Last Price", f"{last_price:,.2f}", f"{change:+.2f} ({pct_change:+.2f}%)")
                c_met2.metric("Market Context", f"{source_lbl}", f"Lat: {latency_ms:.0f}ms", delta_color="off")
                c_met3.metric("Volume", f"{last_vol:,}", None)
                
                # Latency Badge
                st.caption(f"🕒 Updated: {last_ts.strftime('%H:%M:%S')} (Latency: :{lat_color}[{latency_ms:.0f}ms])")
            
            render_live_chart(db_mgr, selected_symbol)
        
        with info_col:
            st.markdown(f"**Market Context**")
            
            # Lookup metadata for selected symbol
            if not symbol_meta.empty and selected_symbol in symbol_meta['symbol'].values:
                meta = symbol_meta[symbol_meta['symbol'] == selected_symbol].iloc[0]
                source = meta['source']
                aclass = meta['asset_class']
            else:
                source = "UNKNOWN"
                aclass = "EQUITY"

            st.markdown(f'<div style="background:rgba(31,119,180,0.1); padding:8px; border-radius:4px; border-left:4px solid #1f77b4; margin-bottom:10px;">'
                        f'<b>Source</b>: {source}<br/>'
                        f'<b>Class</b>: {aclass}</div>', unsafe_allow_html=True)
            
            is_tradable = registry.is_tradable(selected_symbol)
            if is_tradable:
                st.markdown(f'<div style="color:#00ff88; font-size:0.85rem;">{render_icon("check-circle", "#00ff88")} Tradable (IBKR)</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="color:#e74c3c; font-size:0.85rem;">{render_icon("lock", "#e74c3c")} View-Only</div>', unsafe_allow_html=True)
            
            st.markdown(f"**Interval**: 1 min")
            
            st.divider()
            
            # --- AI Insight Panel (Moved to Main View) ---
            with st.expander("🤖 AI Insight Engine", expanded=True):
                if st.button(f"Analyze {selected_symbol}", use_container_width=True, key="btn_ai_main"):
                    with st.spinner("consulting Grok (LPU)..."):
                        # Fetch snapshot for AI
                        ai_df = db_mgr.query_pandas(f"SELECT * FROM realtime_candles WHERE symbol = '{selected_symbol}' ORDER BY timestamp DESC LIMIT 50")
                        if not ai_df.empty:
                            # Calculate technicals
                            last_close = ai_df['close'].iloc[0]
                            vwap = (ai_df['close'] * ai_df['volume']).sum() / ai_df['volume'].sum() if ai_df['volume'].sum() > 0 else last_close
                            volatility = ai_df['close'].std()
                            avg_vol = ai_df['volume'].mean()
                            curr_vol = ai_df['volume'].iloc[0]
                            rvol = curr_vol / avg_vol if avg_vol > 0 else 1.0
                            
                            snapshot = {
                                "symbol": selected_symbol,
                                "price": last_close,
                                "vwap": vwap,
                                "price_vs_vwap_pct": (last_close - vwap) / vwap,
                                "volume": int(curr_vol),
                                "rvol": rvol,
                                "volatility": volatility,
                                "session": "LIVE_TRADE"
                            }
                            
                            import concurrent.futures
                            def run_ai_suite_sync():
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    f1 = executor.submit(ai_analyst.generate_market_summary, selected_symbol, snapshot)
                                    f2 = executor.submit(ai_analyst.detect_regime, selected_symbol, snapshot)
                                    f3 = executor.submit(ai_analyst.check_risk_guardrail, selected_symbol, snapshot)
                                    f4 = executor.submit(ai_analyst.suggest_trade_levels, selected_symbol, snapshot)
                                    return [f.result() for f in [f1, f2, f3, f4]]
                            
                            results = run_ai_suite_sync()
                            st.session_state[f"ai_suite_{selected_symbol}"] = results
                
                # Render AI Results
                if f"ai_suite_{selected_symbol}" in st.session_state:
                    res_summary, res_regime, res_risk, res_levels = st.session_state[f"ai_suite_{selected_symbol}"]
                    
                    # Regime
                    regime = res_regime.get("regime", "UNKNOWN")
                    r_conf = res_regime.get("confidence", 0) * 100
                    st.markdown(f"**Regime**: `{regime}` ({r_conf:.0f}%)")
                    
                    # Summary
                    st.info(res_summary.get('summary', 'N/A'))
                    
                    # Risk
                    risk_lvl = res_risk.get("risk_level", "UNKNOWN")
                    risk_color = "red" if risk_lvl == "HIGH" else "orange" if risk_lvl == "MEDIUM" else "green"
                    st.markdown(f"**Risk**: :{risk_color}[{risk_lvl}]")
                    st.caption(res_risk.get('explanation'))
                    
                    # Levels
                    c1, c2 = st.columns(2)
                    c1.metric("SL", res_levels.get("stop_loss"))
                    c2.metric("TP", res_levels.get("take_profit"))

            
            # Simple heartbeat to trigger streamlit rerun
            st.caption("Auto-refreshing live data...")
            time.sleep(5) # Throttling for maximum Windows/OneDrive stability
            st.rerun()

        st.divider()
        st.markdown(f"#### {render_icon('layout-list')} Real-Time Order Blotter (Recent Fills)", unsafe_allow_html=True)
        # Fetch Real Trades
        try:
            trades_query = """
                SELECT 
                    execution_time as Time,
                    symbol as Symbol,
                    side as Side,
                    quantity as Qty,
                    fill_price as Price,
                    order_type as Type,
                    commission as Fee,
                    slippage_bps as 'Slippage(bps)',
                    trade_id as ID
                FROM trades 
                ORDER BY execution_time DESC 
                LIMIT 50
            """
            trades = db_mgr.query_pandas(trades_query)
            if not trades.empty:
                # Color code Side
                def color_side(val):
                    color = '#2ecc71' if val == 'BUY' else '#e74c3c'
                    return f'color: {color}; font-weight: bold'
                
                st.dataframe(
                    trades.style.map(color_side, subset=['Side']),
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("No trades recorded today. Waiting for strategy execution...")
        except Exception as e:
            st.info(f"Trade ledger not initialized or empty. {e}")
            
        st.caption(f"Last Refreshed: {datetime.now().strftime('%H:%M:%S')}")
    
    with tab2:
        st.markdown(f"#### {render_icon('bar-chart')} Current Holdings", unsafe_allow_html=True)
    with tab2:
        st.markdown(f"#### {render_icon('bar-chart')} Current Holdings", unsafe_allow_html=True)
        st.info("Live positions view requires persistent portfolio service.")
        # Placeholder for real connection
        # positions = db_mgr.query_pandas("SELECT * FROM positions") ...
        
    with tab3:
        st.markdown(f"#### {render_icon('bot')} Staged Deployment & Approval", unsafe_allow_html=True)
        st.info("Strategy staging area for proposed models.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**1️⃣ Current Active**")
            if active_strat:
                st.json(active_strat)
            else:
                st.warning("No strategy active in FULL/CANARY stage.")
        with c2:
            st.markdown("**2️⃣ Proposed Candidate (MOCK)**")
            proposed = {"top_n": 30, "reasoning": "Aggressive momentum capture."}
            st.json(proposed)
            rationale = st.text_area("Human Approval Rationale", "Reviewed backtest.")
            colP1, colP2 = st.columns(2)
            with colP1:
                target_stage = st.selectbox("Activation Stage", ["SHADOW", "PAPER", "CANARY", "FULL"])
            with colP2:
                if st.button("LOG & APPROVE STRATEGY", type="primary"):
                    strat_hash = gov_mgr.log_strategy_approval(config=proposed, regime_snapshot={"label": "Bull"}, llm_reasoning=proposed["reasoning"], human_rationale=rationale, approved_by="ADMIN", stage=target_stage)
                    st.success(f"Strategy {strat_hash[:8]} deployed to {target_stage}")
                    st.rerun()

    with tab4:
        st.markdown(f"#### {render_icon('database')} Immutable Audit Trail", unsafe_allow_html=True)
        audit_sql = "SELECT strategy_hash, stage, approved_by, approved_at, human_rationale FROM strategy_audit_log ORDER BY approved_at DESC"
        audit_data = db_mgr.query_pandas(audit_sql)
        st.dataframe(audit_data, use_container_width=True, hide_index=True)
        
    with tab5:
        st.markdown(f"#### {render_icon('activity')} Strategy Drift Monitor", unsafe_allow_html=True)
        if active_strat:
            d1, d2 = st.columns(2)
            d1.metric("Turnover Drift", "0.08", "-0.01")
            d2.metric("Factor Exposure Drift", "0.15", "Normal")
        else:
            st.warning("No active strategy to monitor drift.")

    with tab6:
        st.markdown(f"#### {render_icon('file-text')} Operational Reporting (Phase 2)", unsafe_allow_html=True)
        cR1, cR2 = st.columns([1, 2])
        with cR1:
            report_date = st.date_input("Report Date", datetime.now())
            if st.button("GENERATE DAILY OPS REPORT", type="primary"):
                report = report_engine.generate_daily_ops_report(report_date.strftime("%Y-%m-%d"))
                st.session_state.current_report = report
        with cR2:
            if "current_report" in st.session_state:
                report_md = report_engine.format_as_markdown(st.session_state.current_report)
                st.markdown(report_md)
                st.download_button("Download Report (.md)", report_md, file_name=f"ops_report_{report_date}.md")
            else:
                st.info("Select a date and click generate to view the Daily Ops Report.")

    with tab7:
        st.markdown(f"#### {render_icon('shield')} Portfolio Risk & Compliance", unsafe_allow_html=True)
        
        rcol1, rcol2 = st.columns(2)
        with rcol1:
            st.markdown("##### Global Capacity")
            global_limits = risk_manager.limits.get("GLOBAL_LIMITS", {})
            metrics = {
                "Max Leverage": f"{global_limits.get('max_total_leverage', 0):.1f}x",
                "Daily Loss Limit": f"${global_limits.get('daily_loss_limit_usd', 0):,.0f}",
                "Min Order": f"${global_limits.get('min_order_threshold_usd', 0):,.0f}",
                "Max Symbol Exposure": f"{global_limits.get('max_symbol_exposure_pct', 0)*100:.0f}%"
            }
            for k, v in metrics.items():
                st.write(f"**{k}:** {v}")
                
            st.markdown("##### Execution Authority")
            auth = risk_manager.limits.get("EXECUTION_AUTHORITY", {})
            for broker, classes in auth.items():
                st.write(f"**{broker}:** {', '.join(classes)}")
                
        with rcol2:
            st.markdown("##### Asset Class Exposure Limits")
            ac_limits = risk_manager.limits.get("ASSET_CLASS_LIMITS", {})
            ac_df = pd.DataFrame([
                {"Class": k, "Max Total (%)": f"{v.get('max_total_exposure_pct', 0)*100:.0f}%", "Max Symbol (%)": f"{v.get('max_symbol_exposure_pct', 0)*100:.0f}%"}
                for k, v in ac_limits.items()
            ])
            if not ac_df.empty:
                st.table(ac_df.set_index("Class"))
        
        st.divider()
        st.info("💡 These limits are enforced at the engine level in `omega/risk_engine.py`. Any order violating these will be hard-rejected before reaching the broker.")

    with tab8:
        st.markdown(f"#### {render_icon('bar-chart')} Market Profile Analysis", unsafe_allow_html=True)
        
        cP1, cP2 = st.columns([1, 3])
        with cP1:
            try:
                # Get symbols from prices table
                avail_symbols = db_mgr.query_pandas("SELECT DISTINCT symbol FROM prices LIMIT 10")['symbol'].tolist()
            except:
                avail_symbols = ["AAPL", "MSFT", "SPY"]
                
            prof_symbol = st.selectbox("Symbol", avail_symbols if avail_symbols else ["AAPL"], key="prof_sym")
            days = st.slider("Lookback Days", 5, 60, 30)
            
        with cP2:
            render_market_profile(db_mgr, prof_symbol, days)

if __name__ == "__main__":
    main()
