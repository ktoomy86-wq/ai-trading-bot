import os
import json
import logging
import time
import requests
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

def clean_json(text: str) -> str:
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text

def get_omni_system_prompt(symbol, lang="ar", supports=[], resistances=[], chat_context=""): 
    lang_instruction = "Arabic language" if lang == "ar" else "English language"
    return f"""You are the complete {symbol} AI Trading Ecosystem, composed of specialized micro-agents:
1. MTF Agent (Multi-Timeframe): Analyzes Daily and 4H macro-trend to restrict 1H trades against the trend.
2. Volume & Liquidity Agent: Reads volume profile to detect Smart Money Concepts, fakeouts, and liquidity sweeps.
3. Pattern Recognition Agent: Detects classic patterns (Head & Shoulders, Double Tops/Bottoms, Wedges) and harmonic patterns.
4. Sentiment & Breaking News Agent: Assesses market sentiment and breaking news impact (e.g. from X or major news outlets) on {symbol}.
5. Chief Strategist: Synthesizes everything into a final Action (BUY/SELL/HOLD). This determines the direction of the trade!
6. Risk Agent: Calculates Stop Loss dynamically using Daily ATR * 1.5 based on the Chief Strategist's Action. Calculate Lot Size so risk = 1% of Account Balance. CRITICAL MANDATORY RULE: YOU MUST ALWAYS SET "status": "APPROVED". Sets TP1 (1:1), TP2 (1:2), TP3 (1:3).
7. Execution Agent: Formats the final trade order.

CRITICAL ALIGNMENT RULE: ALL AGENTS (Risk, Execution, and Strategist) MUST STRICTLY AGREE ON THE SAME DIRECTION (BUY or SELL).
- IF THE OVERALL DECISION IS **BUY**: execution_agent.action MUST be BUY, strategist_agent.Action MUST be BUY. Risk and Execution TP values MUST be HIGHER than Entry Price. SL MUST be LOWER than Entry Price.
- IF THE OVERALL DECISION IS **SELL**: execution_agent.action MUST be SELL, strategist_agent.Action MUST be SELL. Risk and Execution TP values MUST be LOWER than Entry Price. SL MUST be HIGHER than Entry Price.
Any mathematical contradiction (e.g. Action is SELL but TP is higher than Entry) is strictly forbidden.

CRITICAL TRANSLATION RULE: You MUST translate all textual values inside the JSON (such as reasons, chain of thought, summaries, pattern names, sentiments) into the '{lang_instruction}'. The JSON keys must remain in English, but the VALUES must be strictly in {lang_instruction}.

You MUST output ONLY a valid JSON object in this exact structure, with NO extra text or markdown:
{{
  "mtf_agent": {{
    "daily_trend": "BULLISH / BEARISH / CONSOLIDATING",
    "h4_trend": "BULLISH / BEARISH / CONSOLIDATING",
    "trend_strength": 8,
    "permission_to_trade": true
  }},
  "volume_agent": {{
    "smart_money_zones": [4000.50, 4100.00],
    "liquidity_score": 7,
    "fakeout_detected": false
  }},
  "pattern_agent": {{
    "detected_patterns": ["Double Bottom", "Bull Flag"],
    "pattern_confidence": 85
  }},
  "sentiment_agent": {{
    "overall_sentiment": "BULLISH / BEARISH / NEUTRAL (Translated)",
    "sentiment_score": 6,
    "breaking_news_alert": "None / Alert details...",
    "market_fear_greed": 65
  }},
  "strategist_agent": {{
    "Action": "BUY / SELL / HOLD",
    "Confidence_Score": 85,
    "Chain_of_Thought": "...",
    "Execution_Summary": "..."
  }},
  "risk_agent": {{
    "status": "APPROVED",
    "reason": "...",
    "sl_price": 0.0,
    "tp1": 0.0,
    "tp2": 0.0,
    "tp3": 0.0
  }},
  "execution_agent": {{
    "action": "BUY / SELL / HOLD (Must strictly match strategist_agent.Action)",
    "symbol": "{symbol}",
    "lot_size": 0.0,
    "entry_price": 0.0,
    "sl": 0.0,
    "tp": 0.0
  }}
}}
"""

def chat_with_omni_ai(messages, context, lang="ar"):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "⚠️ رمز Groq (GROQ_API_KEY) غير موجود. يرجى إضافته." if lang == "ar" else "⚠️ Groq Token is missing."

    system_persona = f"""You are the 'OmniTrade AI Smart Advisor' (المستشار الذكي), an elite trading strategist and market analyst. You are a genius trader with deep market knowledge. 
Your goal is to answer the user's questions about the market, trading strategies, or the AI's recent decisions.
Here is the LATEST AI ecosystem analysis report (JSON format) and market context. Use it to inform your answers if the user asks about the current setup:
{context}

Respond entirely in {'Arabic' if lang == 'ar' else 'English'}. Be confident, professional, and analytical. Use formatting (bolding, lists) to make your response easy to read.
CRITICAL RULE: DO NOT use LaTeX math formatting (like \\frac or \\text) or brackets for math. Write numbers and equations clearly and plainly. ALWAYS round all numbers, lots, and prices to a maximum of 2 decimal places (e.g., 4000.50 instead of 4053.3999)."""

    # Format messages for the API (only keeping system and previous user/assistant)
    formatted_messages = [{"role": "system", "content": system_persona}]
    for msg in messages[-10:]: # keep last 10 messages for context
        formatted_messages.append({"role": msg["role"], "content": msg["content"]})

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant", # use fast/high-limit model for chat
        "messages": formatted_messages,
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"عذراً، حدث خطأ في الاتصال بالذكاء الاصطناعي: {response.status_code}" if lang == "ar" else f"Error: {response.status_code}"
    except Exception as e:
        return f"حدث خطأ: {str(e)}" if lang == "ar" else f"Error: {str(e)}"

def get_omni_analysis(symbol: str, h4_data: str, h1_data: str, tech_summary: str, macro_data: str, balance: float, atr: float, lang="ar", supports=[], resistances=[], chat_context=""): 
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        err = "لم تقم بإدخال مفتاح Groq API في ملف .env." if lang == "ar" else "Groq API Key is missing from .env."
        return None, err
        
    user_prompt = f"""
Please perform a complete ecosystem analysis for {symbol}.

[H4 Timeframe Data]
{h4_data}

[H1 Timeframe Data]
{h1_data}

[Technical Indicators Summary]
{tech_summary}

[Fundamental Macro Data]
{macro_data}

[Risk Management Parameters]
Account Balance: ${balance}
Daily ATR: {atr}

Provide your analysis in the strict unified JSON format requested.
"""
    max_retries = 3
    base_delay = 5
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    model = "llama-3.1-8b-instant"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": get_omni_system_prompt(symbol, lang, supports, resistances, chat_context)},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }
        
    for attempt in range(max_retries):
        try:
            logger.info(f"Sending Omni-Data to Groq for {symbol}...")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 429:
                logger.warning(f"Rate limit hit. Retrying in {base_delay}s...")
                time.sleep(base_delay)
                base_delay += 5
                continue
                
            response.raise_for_status()
            response_data = response.json()
            
            model_text = response_data['choices'][0]['message']['content']
                
            return json.loads(clean_json(model_text)), None
            
        except requests.exceptions.RequestException as e:
            err_msg = f"Network error calling Groq API: {e}"
            if hasattr(e, 'response') and e.response is not None:
                err_msg += f"\nResponse: {e.response.text}"
            logger.error(err_msg)
            if attempt == max_retries - 1:
                return None, err_msg
            time.sleep(base_delay)
        except (json.JSONDecodeError, KeyError) as e:
            text_val = locals().get('model_text', 'Not available')
            err_msg = f"Error parsing model response: {e}\nResponse text: {text_val}"
            logger.error(err_msg)
            return None, err_msg
            
    return None, f"تم تجاوز الحد الأقصى للمحاولات (Rate Limit). يرجى الانتظار دقيقة والمحاولة مرة أخرى. آخر حالة: {getattr(locals().get('response'), 'status_code', 'Unknown')}" if lang == "ar" else f"Rate limit exceeded. Please wait a minute and try again. Last status: {getattr(locals().get('response'), 'status_code', 'Unknown')}"
