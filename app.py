import streamlit as st
import json
import logging
import os
import plotly.graph_objects as go
import fetcher_data
import importlib
import time
import importlib
import translations as tr_module
importlib.reload(tr_module)
translations = tr_module.translations

importlib.reload(fetcher_data)
# Re-import the functions after reload to update references in the current namespace
from fetcher_data import get_historical_data, get_account_balance, get_daily_atr, execute_mt5_trade, get_support_resistance
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

    /* Premium Dark UI - Smartphone Vibe */
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(145deg, #090B10 0%, #1A1F2D 100%);
    }}
    
    [data-testid="stSidebar"] {{
        background: rgba(9, 11, 16, 0.85) !important;
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255,255,255,0.05);
    }}

    [data-testid="stHeader"] {{
        background: transparent !important;
    }}

    /* Glassmorphic Cards */
    .custom-card, div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(30, 41, 59, 0.4) !important;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
        padding: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }}
    
    .custom-card:hover, div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
    }}

    /* Titles & Typography */
    h1, h2, h3 {{
        color: #F8FAFC !important;
        letter-spacing: 0.5px;
    }}
    
    p, span, div {{
        color: #94A3B8;
    }}

    .main-title {{
        text-align: center;
        background: -webkit-linear-gradient(45deg, #38BDF8, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        font-size: 3rem !important;
        margin-bottom: 30px;
        text-shadow: 0px 4px 20px rgba(56, 189, 248, 0.3);
    }}
    
    /* Sleek Neo-Buttons */
    .stButton>button {{
        background: linear-gradient(90deg, #3B82F6 0%, #8B5CF6 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
        transition: all 0.3s ease !important;
    }}
    
    .stButton>button:hover {{
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 8px 25px rgba(139, 92, 246, 0.6) !important;
    }}

    /* Metric Cards */
    .metric-card {{
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        transition: all 0.2s ease;
    }}
    .metric-card:hover {{
        background: rgba(255, 255, 255, 0.07);
        border-color: rgba(56, 189, 248, 0.3);
    }}
    .metric-value {{
        font-size: 1.8rem;
        font-weight: 900;
        color: #38BDF8;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
    }}
    .metric-label {{
        font-size: 0.95rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    /* Progress bars */
    .stProgress > div > div > div > div {{
        background-color: #8B5CF6 !important;
    }}
    
    /* Hide default elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Blend logo with background seamlessly */
    [data-testid="stImage"] img {{
        mix-blend-mode: screen;
        pointer-events: none;
        user-select: none;
    }}

    /* --- Responsive Mobile & Tablet Design --- */
    @media (max-width: 768px) {{
        .main-title {{
            font-size: 2rem !important;
            margin-bottom: 15px !important;
        }}
        .custom-card {{
            padding: 10px !important;
        }}
        .custom-card h1 {{
            font-size: 2rem !important;
        }}
        .custom-card h3 {{
            font-size: 1.4rem !important;
        }}
        .custom-card p {{
            font-size: 0.9rem !important;
            line-height: 1.4 !important;
        }}
        .metric-value {{
            font-size: 1.4rem !important;
        }}
        .metric-label {{
            font-size: 0.8rem !important;
        }}
        /* Make TradingView iframe fit better on mobile */
        .tradingview-widget-container {{
            height: 400px !important;
        }}
    }}
    
    @media (max-width: 480px) {{
        .main-title {{
            font-size: 1.5rem !important;
        }}
        .custom-card h1 {{
            font-size: 1.8rem !important;
        }}
    }}
    </style>

""", unsafe_allow_html=True)

col_logo1, col_logo2, col_logo3 = st.columns([1, 2.5, 1])
with col_logo2:
    st.image("ecosystem_logo.png", use_container_width=True)


with st.sidebar:
    st.markdown(f"<h1 style='text-align: center;'>{t['sidebar_title']}</h1>", unsafe_allow_html=True)
    
    st.header(t["symbol_select"])
    selected_symbol = st.selectbox("", ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "US30"], label_visibility="collapsed")
    
    st.header(t["timeframe_select"])
    selected_timeframe = st.selectbox("", ["15m", "1h", "1d", "1wk", "1mo"], index=1, label_visibility="collapsed")
    
    st.header(t["config_header"])
    api_key = st.text_input(t["github_token"], type="password", value=os.getenv("GITHUB_TOKEN", ""))
    tg_token = st.text_input(t.get("telegram_token", "Telegram Token"), type="password", value=os.getenv("TG_TOKEN", ""))
    tg_chat = st.text_input(t.get("chat_id", "Chat ID"), value=os.getenv("TG_CHAT", ""))
    
    st.markdown("---")
    st.markdown(t["system_status"])
    st.success(t["ready"])
    
    st.markdown("---")
    
    
import requests

import streamlit.components.v1 as components

def render_tradingview_chart(symbol, timeframe, lang_code):
    tv_interval_map = {
        "15m": "15",
        "1h": "60",
        "1d": "D",
        "1wk": "W",
        "1mo": "M"
    }
    tv_interval = tv_interval_map.get(timeframe, "60")
    tv_locale = "ar_AE" if lang_code == "ar" else "en"
    
    prefix = "FX:"
    if symbol in ["BTCUSD", "ETHUSD"]:
        prefix = "CRYPTO:"
    elif symbol == "US30":
        prefix = "CAPITALCOM:"
    
    components.html(
        f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container" style="height:100%;width:100%">
          <div id="tradingview_chart" style="height:calc(100% - 32px);width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget(
          {{
          "height": 600,
          "width": "100%",
          "symbol": "{prefix}{symbol}",
          "interval": "{tv_interval}",
          "timezone": "Etc/UTC",
          "theme": "dark",
          "style": "1",
          "locale": "{tv_locale}",
          "enable_publishing": false,
          "backgroundColor": "rgba(19, 23, 34, 1)",
          "gridColor": "rgba(42, 46, 57, 0.06)",
          "hide_top_toolbar": false,
          "hide_legend": false,
          "save_image": false,
          "container_id": "tradingview_chart"
        }}
          );
          </script>
        </div>
        <!-- TradingView Widget END -->
        """,
        height=600,
    )

if True:
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

    supports, resistances = get_support_resistance(st.session_state.df_primary)
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
                latest_row = df_pri_slim.iloc[-1]
                price = latest_row.get('close', 0.0)
                rsi = latest_row.get('RSI_14', 0.0)
                macd = latest_row.get('MACD_12_26_9', 0.0)
                macd_signal = latest_row.get('MACDs_12_26_9', 0.0)
                vol = latest_row.get('volume', 0.0)
                vol_ma = latest_row.get('Volume_MA_20', 0.0)
                tech_summary = f"Current Price: {price:.4f}\\nRSI (14): {rsi:.2f}\\nMACD: {macd:.4f} (Signal: {macd_signal:.4f})\\nVolume: {vol} (20MA: {vol_ma})"

                chat_context = ""
                if "chat_messages" in st.session_state:
                    chat_context = "\n".join([m['role'] + ": " + m['content'] for m in st.session_state.chat_messages if m['role'] == 'user'])
                new_omni_json, err_msg = get_omni_analysis(selected_symbol, df_sec_slim.to_csv(index=False), df_pri_slim.to_csv(index=False), tech_summary, macro_data, account_balance, daily_atr, lang_code, supports=supports, resistances=resistances, chat_context=chat_context)

                if new_omni_json is None:
                    st.error(t["analysis_fail"].format(err=err_msg))
                else:
                    st.session_state.omni_json = new_omni_json
                    firebase_manager.save_trade_analysis(selected_symbol, selected_timeframe, new_omni_json)
                    
                    # Check for Telegram Webhook
                    strat_data = new_omni_json.get("strategist_agent", {})
                    conf_score = strat_data.get("Confidence_Score", 0)
                    action = strat_data.get("Action", "HOLD")
                    
                    if action in ["BUY", "SELL"] and conf_score > 80 and tg_token and tg_chat:
                        try:
                            exec_data = new_omni_json.get("execution_agent", {})
                            msg = f"🚨 AI Trading Alert: {action} {selected_symbol}\\nConfidence: {conf_score}%\\nEntry: {exec_data.get('entry_price')}\\nSL: {exec_data.get('sl')}"
                            requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", json={"chat_id": tg_chat, "text": msg})
                        except Exception as e:
                            logger.error(f"Telegram webhook failed: {e}")
                            
                    st.rerun()
            else:
                st.error(t["daily_fail"])

    # --- 4. Display AI Analysis ---
    if omni_json:
        mtf_json = omni_json.get("mtf_agent", {})
        vol_json = omni_json.get("volume_liquidity_agent", {})
        pat_json = omni_json.get("pattern_recognition_agent", {})
        sent_json = omni_json.get("sentiment_agent", {})
        risk_json = omni_json.get("risk_agent", {})
        exec_json = omni_json.get("execution_agent", {})
        strat_json = omni_json.get("strategist_agent", {})

        # STRATEGIST AT THE TOP
        if strat_json:
            action = strat_json.get("Action", "HOLD").upper()
            color = "#22C55E" if action == "BUY" else "#EF4444" if action == "SELL" else "#94A3B8"
            
            action_ar = "شراء" if action == "BUY" else "بيع" if action == "SELL" else "انتظار"
            action_display = f"{action_ar} ({action})" if lang_code == 'ar' else action
            
            title = "👑 قرار كبير الاستراتيجيين" if lang_code == "ar" else "👑 Strategist Decision"
            conf_text = "نسبة الثقة" if lang_code == "ar" else "Confidence"
            target_text = "هدف السعر" if lang_code == "ar" else "Target"
            entry_text = "الدخول" if lang_code == "ar" else "Entry"
            
            
            conf_score = strat_json.get('Confidence_Score', 0)
            tp = exec_json.get('tp', 'N/A')
            if isinstance(tp, (int, float)): tp = round(tp, 2)
            entry = exec_json.get('entry_price', 'N/A')
            if isinstance(entry, (int, float)): entry = round(entry, 2)

            
            st.markdown(f"""
            <div class='custom-card' style='margin-top: 20px;'>
                <h3 style='text-align: center; margin-bottom: 10px; font-size: 2rem;'>{title}</h3>
                <h1 style='text-align: center; color: {color}; font-size: 3.5rem; margin-top: 0px;'>{action_display}</h1>
                <p style='text-align: center; color: #94A3B8; font-size: 1.2rem;'>{conf_text}: {conf_score}% | {entry_text}: {entry} | {target_text}: {tp}</p>
                <div style="margin-top: 20px; font-size: 1.1rem; color: #e0e0e0; line-height: 1.8; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                    {strat_json.get('Execution_Summary', '')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            cot = strat_json.get("Chain_of_Thought", "")
            if cot:
                with st.expander(t.get("cot_title", "Chain of Thought")):
                    st.write(cot)
        else:
            st.error(t.get("strat_fail", "Failed"))
            
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            with st.container(border=True):
                st.subheader(t.get("mtf_agent", "MTF Agent"))
                if mtf_json:
                    st.markdown(f"**{t.get('daily_trend', 'Daily Trend:')}** {mtf_json.get('daily_trend', 'N/A')}")
                    st.markdown(f"**{t.get('h4_trend', '4H Trend:')}** {mtf_json.get('h4_trend', 'N/A')}")
                    
                    strength = mtf_json.get('trend_strength', 0)
                    st.markdown(f"**{t.get('trend_strength', 'Trend Strength:')}** {strength}/10")
                    st.progress(strength / 10.0)

                    perm = "✅" if mtf_json.get('permission_to_trade') else "❌"
                    st.markdown(f"**{t.get('permission_to_trade', 'Permission:')}** {perm}")
                else:
                    st.error(t.get("mtf_fail", "Failed"))

            with st.container(border=True):
                st.subheader(t.get("pattern_agent", "Pattern Agent"))
                if pat_json:
                    st.markdown(f"**{t.get('detected_patterns', 'Patterns:')}** {', '.join(pat_json.get('detected_patterns', []))}")
                    conf = pat_json.get('pattern_confidence', 0)
                    st.markdown(f"**{t.get('pattern_confidence', 'Confidence:')}** {conf}%")
                    st.progress(conf / 100.0)
                else:
                    st.error(t.get("pattern_fail", "Failed"))

        with col2:
            with st.container(border=True):
                st.subheader(t.get("volume_agent", "Volume Agent"))
                if vol_json:
                    st.markdown(f"**{t.get('smart_money_zones', 'SMC Zones:')}** {', '.join(str(round(float(z), 2)) for z in vol_json.get('smart_money_zones', []))}")
                    
                    liq = vol_json.get('liquidity_score', 0)
                    st.markdown(f"**{t.get('liquidity_score', 'Liquidity Score:')}** {liq}/10")
                    st.progress(liq / 10.0)

                    fakeout = f"⚠️ {t.get('yes_word', 'Yes')}" if vol_json.get('fakeout_detected') else t.get('no_word', 'No')
                    st.markdown(f"**{t.get('fakeout_detected', 'Fakeout:')}** {fakeout}")
                else:
                    st.error(t.get("volume_fail", "Failed"))

            with st.container(border=True):
                st.subheader(t.get("sentiment_agent", "Sentiment Agent"))
                if sent_json:
                    st.markdown(f"**{t.get('overall_sentiment', 'Sentiment:')}** {sent_json.get('overall_sentiment', 'N/A')}")
                    
                    sent_score = sent_json.get('sentiment_score', 0)
                    st.markdown(f"**{t.get('sentiment_score', 'Score:')}** {sent_score}/10")
                    st.progress(sent_score / 10.0)
                    
                    st.markdown(f"**{t.get('fear_greed', 'Fear/Greed:')}** {sent_json.get('market_fear_greed', 'N/A')}")
                    st.info(f"**{t.get('breaking_news', 'News:')}** {sent_json.get('breaking_news_alert', 'N/A')}")
                else:
                    st.error(t.get("sentiment_fail", "Failed"))

        with col3:
            with st.container(border=True):
                st.subheader(t.get("risk_agent", "Risk Agent"))
                if risk_json:
                    if "APPROVED" in risk_json.get("status", "").upper():
                        st.success(t.get("trade_approved", "Approved"))
                        
                        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t.get('lot_size', 'Lot')}</div><div class='metric-value' style='color:#00ff00;'>{exec_json.get('lot_size', 0)}</div></div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t.get('tp1', 'TP1')}</div><div class='metric-value'>{risk_json.get('tp1', 0)}</div></div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t.get('tp2', 'TP2')}</div><div class='metric-value'>{risk_json.get('tp2', 0)}</div></div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t.get('tp3', 'TP3')}</div><div class='metric-value'>{risk_json.get('tp3', 0)}</div></div>", unsafe_allow_html=True)
                    else:
                        st.error(f"{t.get('trade_rejected', 'Rejected')}\n\n{risk_json.get('reason', '')}")
                else:
                    st.error(t.get("risk_fail", "Failed"))

        # 6. Trade Execution Button
        if risk_json.get("status", "").upper() == "APPROVED" and strat_json.get("Action") in ["BUY", "SELL"]:
            st.markdown("---")
            st.markdown(f"<h2 style='text-align: center;'>{t['sim_title']}</h2>", unsafe_allow_html=True)

            action = strat_json.get("Action")
            lot = exec_json.get("lot_size", 0.01)
            sl = exec_json.get("sl")
            tp = exec_json.get("tp")

            st.info(t["ai_recommend"].format(action=action, symbol=selected_symbol, lot=lot, sl=sl, tp=tp))

            if st.button(t["sim_btn"], use_container_width=True, type="primary"):
                with st.spinner(t["sending_order"]):
                    success, msg = execute_mt5_trade(action, selected_symbol, lot, sl, tp)
                    if success:
                        st.success(f"✅ {msg}")
                        st.balloons()
                    else:
                        st.error(f"❌ {msg}")

        # --- 7. Smart AI Advisor (Chat) ---
        st.markdown("---")
        
        chat_col1, chat_col2, chat_col3 = st.columns([1, 2.5, 1])
        with chat_col2:
            st.markdown("<h2 style='text-align: center; color: #38BDF8;'>💬 المستشار الذكي</h2>", unsafe_allow_html=True)
            
            with st.container(border=True):
                if "chat_messages" not in st.session_state:
                    st.session_state.chat_messages = []
                    st.session_state.chat_messages.append({"role": "assistant", "content": "أهلاً بك أيها المتداول الذكي. أنا المستشار الاستراتيجي لمنظومة OmniTrade AI. هل لديك أي استفسار حول السوق أو قراراتي؟" if lang_code == "ar" else "Hello smart trader. I am the OmniTrade AI strategic advisor. How can I help you with today's market?"})

                for msg in st.session_state.chat_messages:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                        
                if prompt := st.chat_input("اكتب استفسارك هنا (مثال: لماذا رفضت الصفقة؟ أو ما هو اتجاه الذهب؟)" if lang_code == "ar" else "Type your question here..."):
                    st.session_state.chat_messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)
                        
                    with st.chat_message("assistant"):
                        with st.spinner("المستشار يفكر..." if lang_code == "ar" else "Advisor is thinking..."):
                            from agent import chat_with_omni_ai
                            # Context payload is the latest analysis + current price
                            context = str(omni_json)
                            response_text = chat_with_omni_ai(st.session_state.chat_messages, context, lang_code)
                            st.write(response_text)
                            st.session_state.chat_messages.append({"role": "assistant", "content": response_text})

    # --- 5. Live Mode Rerun Loop ---
    

