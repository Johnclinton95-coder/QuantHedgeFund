"""
QS Hedge Fund Dashboard - Operational Control Plane

Refined Streamlit application with live monitors and emergency controls.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import time

# Page configuration
st.set_page_config(
    page_title="QS Control Plane",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# SVG Icons
ICONS = {
    "settings": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
    "shield": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "activity": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    "terminal": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
    "alert": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="red" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    "check": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00ff88" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
}

def render_icon(name, color="#1f77b4"):
    return f'<div style="display:inline-block; vertical-align:middle; margin-right:8px; color:{color};">{ICONS[name]}</div>'

# Session state initialization
if "halted" not in st.session_state:
    st.session_state.halted = False
if "strategy_approved" not in st.session_state:
    st.session_state.strategy_approved = False
if "messages" not in st.session_state:
    st.session_state.messages = []

# Custom CSS
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1f77b4; margin-bottom: 1rem; }
    .status-panel { background: #0e1117; border: 1px solid #1f77b4; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .halt-banner { background: #4a0404; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-bottom: 20px; border: 1px solid red; }
    .metric-value { font-size: 1.5rem; font-weight: bold; }
    .metric-label { color: #888; font-size: 0.9rem; }
    .stButton > button { width: 100%; }
</style>
""", unsafe_allow_html=True)

def main():
    # Sidebar: System Health & Emergency Controls
    with st.sidebar:
        st.markdown(f"### {render_icon('activity')} System Health")
        
        # Health Indicators (Mocked)
        colH1, colH2 = st.columns(2)
        with colH1:
            st.markdown(f"{render_icon('check')} **IBKR API**")
            st.markdown(f"{render_icon('check')} **Data Feed**")
        with colH2:
            st.markdown("🟢 Connected")
            st.markdown("🟢 Live")
            
        st.divider()
        
        # Emergency Controls
        st.markdown(f"### {render_icon('shield', 'red')} Emergency Controls")
        
        if not st.session_state.halted:
            if st.button("🚨 HALT ALL TRADING", type="primary"):
                st.session_state.halted = True
                st.rerun()
        else:
            if st.button("🟢 RESUME TRADING"):
                st.session_state.halted = False
                st.rerun()
                
        if st.button("🔥 CANCEL ALL ORDERS"):
            st.toast("Cancelling all open orders...", icon="🔥")
            
        if st.button("💀 FLATTEN ENTIRE PORTFOLIO"):
            st.warning("Are you sure? This will market sell everything.")
            if st.button("CONFIRM FLATTEN", type="primary"):
                st.toast("Flattening portfolio...", icon="💀")

        st.divider()
        st.markdown(f"### {render_icon('settings')} Config")
        st.text_input("Daily Loss Limit ($)", value="5,000")
        st.text_input("Max Symbol Exp (%)", value="20")

    # Halt Banner
    if st.session_state.halted:
        st.markdown('<div class="halt-banner">⚠️ SYSTEM HALTED - NO TRADES ALLOWED ⚠️</div>', unsafe_allow_html=True)

    # Main Header
    st.markdown(f'<div class="main-header">🛡️ Operational Control Plane</div>', unsafe_allow_html=True)

    # Live Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Net Liquidity", "$5.24M", "+0.4%")
    with col2:
        st.metric("Gross Exposure", "138%", "Normal")
    with col3:
        st.metric("Day P&L", "+$24,510", "0.47%")
    with col4:
        st.metric("Drawdown", "-$12.3k", "Max: $50k")

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Live Blotter",
        "Positions",
        "Strategy AI",
        "Latency Lab",
        "Risk Metrics"
    ])

    with tab1:
        render_blotter()
    
    with tab2:
        render_positions()
        
    with tab3:
        render_strategy_ai()
        
    with tab4:
        render_latency()
        
    with tab5:
        render_risk()

def render_blotter():
    st.markdown(f"### {render_icon('terminal')} Live Order Blotter")
    
    # Sample Order Data
    orders = pd.DataFrame([
        {"ID": "ord_101", "Time": "17:28:01", "Symbol": "AAPL", "Side": "BUY", "Qty": "100", "Filled": "100", "Type": "ADAPTIVE", "Status": "FILLED", "Slippage": "1.2 bps"},
        {"ID": "ord_102", "Time": "17:29:10", "Symbol": "MSFT", "Side": "SELL", "Qty": "50", "Filled": "0", "Type": "LMT", "Status": "SUBMITTED", "Slippage": "-"},
        {"ID": "ord_103", "Time": "17:29:45", "Symbol": "TSLA", "Side": "BUY", "Qty": "200", "Filled": "45", "Type": "ADAPTIVE", "Status": "PARTIAL", "Slippage": "0.8 bps"},
    ])
    
    st.dataframe(orders, use_container_width=True, hide_index=True)

def render_positions():
    st.markdown("### ⚖️ Active Positions")
    positions = pd.DataFrame({
        "Symbol": ["RGTI", "QBTS", "EOSE", "OKLO", "WDC"],
        "Qty": [5000, 2000, 1000, 500, 300],
        "Market Value": ["$520,000", "$210,000", "$98,000", "$45,000", "$32,000"],
        "P&L": ["+$42k", "-$1.2k", "+$5.5k", "+$8k", "-$500"],
        "Exposure %": ["9.9%", "4.0%", "1.9%", "0.9%", "0.6%"]
    })
    st.dataframe(positions, use_container_width=True, hide_index=True)

def render_strategy_ai():
    st.markdown(f"### {render_icon('terminal')} Strategy Approval Gate")
    
    st.warning("An LLM (gpt-oss-120b) has proposed a new strategy configuration based on detected 'Bull Volatile' regime.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Current Strategy (v2)**")
        st.json({
            "momentum_weight": 0.4,
            "value_weight": 0.3,
            "rebalance_freq": "weekly"
        })
    with col2:
        st.markdown("**Proposed Strategy (v3)**")
        st.json({
            "momentum_weight": 0.6,
            "value_weight": 0.2,
            "rebalance_freq": "daily",
            "reasoning": "Higher momentum weight to capture volatility in Bull regim."
        })
    
    if not st.session_state.strategy_approved:
        if st.button("✅ APPROVE & DEPLOY TO LIVE"):
            st.session_state.strategy_approved = True
            st.success("Strategy v3 deployed to Production Engine.")
            st.rerun()
    else:
        st.success("Strategy v3 is currently ACTIVE in Production.")
        if st.button("⏪ REVERT TO v2"):
            st.session_state.strategy_approved = False
            st.rerun()

def render_latency():
    st.markdown("### ⏱️ Latency Observability")
    
    # Mock latency metrics
    l_metrics = {
        "P50 (Market to Signal)": "12ms",
        "P95 (Signal to Submit)": "45ms",
        "P99 (Submit to Ack)": "142ms"
    }
    
    cols = st.columns(3)
    for i, (k, v) in enumerate(l_metrics.items()):
        cols[i].metric(k, v)
        
    # Latency Chart
    chart_data = pd.DataFrame(np.random.randn(20, 3) * 10 + 50, columns=['P50', 'P95', 'P99'])
    st.line_chart(chart_data)

def render_risk():
    st.markdown("### 🛡️ Risk & Limits")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Daily Loss Limit**")
        st.progress(0.24, text="24% consumed ($1,200 / $5,000)")
        
        st.markdown("**Max Leverage**")
        st.progress(0.69, text="1.38x / 2.0x")
    
    with col2:
        st.markdown("**Safety Gates**")
        st.markdown(f"{render_icon('check')} Paper Trading Validated")
        st.markdown(f"{render_icon('check')} Latency Benchmark Met")
        st.markdown(f"{render_icon('alert')} **Real-Money Compliance Check Needed**")

if __name__ == "__main__":
    main()
