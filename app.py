import streamlit as st
import json
import logging
import os
import plotly.graph_objects as go
from fetcher_data import get_historical_data, get_account_balance, get_daily_atr, execute_mt5_trade
import fetcher_data
import importlib
import time
from translations import translations

importlib.reload(fetcher_data)
# Re-import the functions after reload to update references in the current namespace
from fetcher_data import get_historical_data, get_account_balance, get_daily_atr, execute_mt5_trade
from macro_fetcher import fetch_all_macro_data
import agent
importlib.reload(agent)
from agent import get_omni_analysis
import firebase_manager
firebase_manager.init_firebase()

# Setup page config
st.set_page_config(page_title="AI Trading Ecosystem", page_icon="🤖", layout="wide")

# Handle Language Selection
lang_choice = st.sidebar.selectbox("🌐 لغة العرض (Language)", ["العربية (Arabic)", "English"])
lang_code = "ar" if "Arabic" in lang_choice else "en"

if "current_lang" not in st.session_state:
    st.session_state.current_lang = lang_code
elif st.session_state.current_lang != lang_code:
    st.session_state.current_lang = lang_code
    # Clear the AI report if the language changes so it doesn't show in the old language
    if "omni_json" in st.session_state:
        del st.session_state["omni_json"]

st.session_state.lang = lang_code
t = translations[lang_code]

# Dynamic CSS based on language
direction = "rtl" if lang_code == "ar" else "ltr"
text_align = "right" if lang_code == "ar" else "left"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Cairo', sans-serif;
        direction: {direction};
        text-align: {text_align};
    }}
    
    .main-title {{
        text-align: center;
        background: -webkit-linear-gradient(#f0b90b, #f7d24a);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        font-size: 2.5rem !important;
        margin-bottom: 30px;
    }}
    
    .decision-box {{
        background: linear-gradient(135deg, rgba(240, 185, 11, 0.15), rgba(240, 185, 11, 0.05));
        border-{'right' if lang_code == 'ar' else 'left'}: 5px solid #f0b90b; 
        padding: 25px;
        border-radius: 12px;
        margin-top: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }}
    
    .stButton>button {{
        background-color: #f0b90b;
        color: #000;
        font-weight: bold;
        font-size: 1.2rem;
        border: none;
        border-radius: 8px;
    }}
    .stButton>button:hover {{
        background-color: #f7d24a;
        color: #000;
    }}
    
    .metric-card {{
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        margin-bottom: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    
    .metric-value {{
        font-size: 1.5rem;
        font-weight: bold;
        color: #f0b90b;
    }}
    
    .metric-label {{
        font-size: 0.9rem;
        color: #a0a0a0;
    }}
</style>
""", unsafe_allow_html=True)

st.markdown(f'<h1 class="main-title">{t["title"]}</h1>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"<h1 style='text-align: center;'>{t['sidebar_title']}</h1>", unsafe_allow_html=True)
    
    st.header(t["symbol_select"])
    selected_symbol = st.selectbox("", ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "US30"], label_visibility="collapsed")
    
    st.header(t["timeframe_select"])
    selected_timeframe = st.selectbox("", ["15m", "1h", "1d", "1wk"], index=1, label_visibility="collapsed")
    
    st.header(t["config_header"])
    api_key = st.text_input(t["github_token"], type="password", value=os.getenv("GITHUB_TOKEN", ""))
    
    st.markdown("---")
    st.markdown(t["system_status"])
    st.success(t["ready"])
    
    st.markdown("---")
    live_mode = st.toggle(t["live_mode"], value=False)

import streamlit.components.v1 as components

def render_tradingview_chart(symbol, timeframe, lang_code):
    tv_interval_map = {
        "15m": "15",
        "1h": "60",
        "1d": "D",
        "1wk": "W"
    }
    tv_interval = tv_interval_map.get(timeframe, "60")
    tv_locale = "ar_AE" if lang_code == "ar" else "en"
    
    # Prefix mapping for standard forex/crypto pairs on TV
    prefix = "FX:"
    if symbol in ["BTCUSD", "ETHUSD"]:
        prefix = "CRYPTO:"
    elif symbol == "US30":
        prefix = "CAPITALCOM:"
        
    tv_symbol = f"{prefix}{symbol}"
    
    html_code = f"""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container" style="height:600px;width:100%">
      <div id="tradingview_12345" style="height:600px;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
      "autosize": true,
      "symbol": "{tv_symbol}",
      "interval": "{tv_interval}",
      "timezone": "Etc/UTC",
      "theme": "dark",
      "style": "1",
      "locale": "{tv_locale}",
      "enable_publishing": false,
      "backgroundColor": "rgba(0, 0, 0, 1)",
      "gridColor": "rgba(255, 255, 255, 0.06)",
      "hide_top_toolbar": false,
      "hide_legend": false,
      "save_image": false,
      "container_id": "tradingview_12345",
      "toolbar_bg": "#f1f3f6",
      "withdateranges": true,
      "allow_symbol_change": true,
      "studies": [
        "RSI@tv-basicstudies",
        "MACD@tv-basicstudies"
      ]
    }}
      );
      </script>
    </div>
    <!-- TradingView Widget END -->
    """
    
    components.html(html_code, height=650, width=None)


# --- 1. Fetch Live Market Data First ---
st.markdown("---")
if "df_primary" not in st.session_state:
    with st.spinner(t["fetching_market"].format(symbol=selected_symbol)):
        df_primary = get_historical_data(selected_symbol, selected_timeframe)
else:
    df_primary = get_historical_data(selected_symbol, selected_timeframe)

if df_primary is None:
    st.error(t["fetch_failed"].format(symbol=selected_symbol))
    st.stop()

st.session_state.df_primary = df_primary
st.session_state.selected_symbol = selected_symbol
st.session_state.selected_timeframe = selected_timeframe

# --- 2. Interactive Live Chart ---
omni_json = st.session_state.get("omni_json", None)

st.markdown(f"<h2 style='text-align: center;'>{t['live_chart'].format(symbol=selected_symbol, timeframe=selected_timeframe)} (TradingView)</h2>", unsafe_allow_html=True)

render_tradingview_chart(selected_symbol, selected_timeframe, lang_code)

st.markdown("---")

# --- 3. AI Analysis Trigger ---
if st.button(t["ai_update_btn"], use_container_width=True, type="primary"):
    if not api_key:
        st.error(t["missing_token"])
        st.stop()
        
    os.environ["GITHUB_TOKEN"] = api_key
    
    with st.spinner(t["processing_ai"]):
        df_secondary = get_historical_data(selected_symbol, '1d')
        
        macro_data = fetch_all_macro_data(selected_symbol)
        account_balance = get_account_balance()
        daily_atr = get_daily_atr(selected_symbol)
        
        df_sec_slim = df_secondary.tail(50).round(4) if df_secondary is not None else None
        df_pri_slim = df_primary.tail(50).round(4)
        
        if df_sec_slim is not None:
            new_omni_json, err_msg = get_omni_analysis(selected_symbol, df_sec_slim.to_csv(index=False), df_pri_slim.to_csv(index=False), macro_data, account_balance, daily_atr, lang_code)
            
            if new_omni_json is None:
                st.error(t["analysis_fail"].format(err=err_msg))
            else:
                st.session_state.omni_json = new_omni_json
                firebase_manager.save_trade_analysis(selected_symbol, selected_timeframe, new_omni_json)
                st.rerun()
        else:
            st.error(t["daily_fail"])

# --- 4. Display AI Analysis ---
if omni_json:
    tech_json = omni_json.get("technical_agent", {})
    macro_json = omni_json.get("macro_agent", {})
    risk_json = omni_json.get("risk_agent", {})
    strat_json = omni_json.get("strategist_agent", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.subheader(t["tech_agent"])
            if tech_json:
                st.markdown(f"**{t['current_trend']}** {tech_json.get('current_trend', 'N/A')}")
                st.markdown(f"**{t['momentum']}** {tech_json.get('momentum', 'N/A')}")
                st.markdown(f"**{t['struct_shifts']}** {tech_json.get('structural_shifts', 'N/A')}")
                
                st.markdown(f"**{t['sr_zones']}**")
                for zone in tech_json.get('support_resistance_zones', []):
                    st.markdown(f"- {zone}")
                
                st.markdown("---")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">{t['entry_price']}</div>
                        <div class="metric-value">{tech_json.get('suggested_entry_price', 0)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">{t['sl']}</div>
                        <div class="metric-value" style="color:#ff4b4b;">{tech_json.get('suggested_stop_loss', 0)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                conf = tech_json.get('technical_confidence_score', 0)
                st.progress(conf / 100.0, text=f"{t['conf']} {conf}%")
            else:
                st.error(t["tech_fail"])
        
    with col2:
        with st.container(border=True):
            st.subheader(t["macro_agent"])
            if macro_json:
                bias = macro_json.get('fundamental_bias', 'Neutral')
                color = "#00ff00" if bias.lower() == "bullish" else "#ff0000" if bias.lower() == "bearish" else "#aaaaaa"
                
                st.markdown(f"**{t['fund_bias']}** <span style='color:{color}; font-weight:bold; font-size:1.2rem;'>{bias}</span>", unsafe_allow_html=True)
                st.markdown(f"**{t['news_impact']}** {macro_json.get('impact_severity_score', 'N/A')}")
                
                st.info(f"**{t['macro_summary']}**\n\n{macro_json.get('macro_factors_summary', '')}")
            else:
                st.error(t["macro_fail"])
        
    with col1:
        with st.container(border=True):
            st.subheader(t["risk_agent"])
            if risk_json:
                if risk_json.get("status") == "APPROVED":
                    st.success(t["trade_approved"])
                    
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t['lot_size']}</div><div class='metric-value' style='color:#00ff00;'>{risk_json.get('lot_size')}</div></div>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t['tp1']}</div><div class='metric-value'>{risk_json.get('tp1')}</div></div>", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t['tp2']}</div><div class='metric-value'>{risk_json.get('tp2')}</div></div>", unsafe_allow_html=True)
                    with c4:
                        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t['tp3']}</div><div class='metric-value'>{risk_json.get('tp3')}</div></div>", unsafe_allow_html=True)
                else:
                    st.error(f"{t['trade_rejected']}\n\n{risk_json.get('reason')}")
            else:
                st.error(t["risk_fail"])
        
    with col2:
        with st.container(border=True):
            st.subheader(t["strat_agent"])
            if strat_json:
                action = strat_json.get("Action", "HOLD")
                color = "#00ff00" if action == "BUY" else "#ff4b4b" if action == "SELL" else "#aaaaaa"
                st.markdown(f"""
                <div class="decision-box">
                    <div style="font-size: 1.2rem; margin-bottom: 5px;">{t['final_decision']} ({selected_symbol}):</div>
                    <span style="color: {color}; font-size: 2.8rem; font-weight: 900;">{action}</span>
                    <hr style="border-color: rgba(255,255,255,0.1);">
                    <div style="font-size: 1.1rem; display: flex; justify-content: space-between;">
                        <span><strong>{t['entry']}</strong> {strat_json.get('Entry_Price', 'N/A')}</span>
                        <span><strong>{t['confidence']}</strong> {strat_json.get('Confidence_Score', 0)}%</span>
                    </div>
                    <div style="margin-top: 15px; font-size: 1rem; color: #e0e0e0; line-height: 1.6; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;">
                        {strat_json.get('Execution_Summary', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(t["strat_fail"])

    # 6. Trade Execution Button
    if risk_json.get("status") == "APPROVED" and strat_json.get("Action") in ["BUY", "SELL"]:
        st.markdown("---")
        st.markdown(f"<h2 style='text-align: center;'>{t['sim_title']}</h2>", unsafe_allow_html=True)
        
        action = strat_json.get("Action")
        lot = risk_json.get("lot_size", 0.01)
        sl = risk_json.get("sl_price")
        tp = risk_json.get("tp1") # Defaulting to TP1
        
        st.info(t["ai_recommend"].format(action=action, symbol=selected_symbol, lot=lot, sl=sl, tp=tp))
        
        if st.button(t["sim_btn"], use_container_width=True, type="primary"):
            with st.spinner(t["sending_order"]):
                success, msg = execute_mt5_trade(action, selected_symbol, lot, sl, tp)
                if success:
                    st.success(f"✅ {msg}")
                    st.balloons()
                else:
                    st.error(f"❌ {msg}")
                    
    # 7. Trade History from Firebase
    st.markdown("---")
    history_title = "سجل الصفقات السابقة" if lang_code == "ar" else "Previous Trade History"
    st.markdown(f"<h2 style='text-align: center;'>{history_title}</h2>", unsafe_allow_html=True)
    with st.expander("عرض السجل (View History)" if lang_code == "ar" else "View History"):
        history = firebase_manager.get_trade_history(limit=10)
        if not history:
            st.info("لا توجد صفقات محفوظة أو أن الاتصال بـ Firebase غير مفعل." if lang_code == "ar" else "No saved trades or Firebase is not connected.")
        else:
            for item in history:
                action_col = "#00ff00" if item.get('action') == "BUY" else "#ff4b4b" if item.get('action') == "SELL" else "#aaaaaa"
                st.markdown(f"**{item.get('symbol')}** | {item.get('timestamp')[:19]} | Action: <span style='color:{action_col}; font-weight:bold;'>{item.get('action')}</span>", unsafe_allow_html=True)

# --- 5. Live Mode Rerun Loop ---
if live_mode:
    time.sleep(1)
    st.rerun()
