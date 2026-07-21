import os
import json
import logging
import time
import requests
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
5. Risk Agent: Calculates Stop Loss dynamically using Daily ATR * 1.5. Dynamically calculate and adjust the Lot Size so that total risk NEVER exceeds 1% of Account Balance. DO NOT REJECT the trade for exceeding risk; instead, reduce the Lot Size. Sets TP1 (1:1), TP2 (1:2), TP3 (1:3). Only reject if the required lot size is less than 0.01.
6. Execution Agent: Formats the final trade order for programmatic execution. CRITICAL: Ensure `tp` and `sl` are logically placed based on the Action. For BUY, TP MUST be greater than Entry, and SL MUST be less than Entry. For SELL, TP MUST be less than Entry, and SL MUST be greater than Entry.
7. Chief Strategist: Synthesizes everything into a final Action (BUY/SELL/HOLD).

Here is the algorithmic analysis of support and resistance on the chart for {symbol}:
- Supports: {supports}
- Resistances: {resistances}
Incorporate these levels when deciding stop loss, take profit, and smart money zones.

User's Custom Instructions & Capital (from Chat History):
{chat_context}
(Use this to strictly adjust the Account Balance and strategy if the user requested it).

You must output a SINGLE JSON object containing all 7 reports precisely in this format.
IMPORTANT: All string values, explanations, summaries, and reasons inside the JSON MUST be written in the {lang_instruction}.
If the language is Arabic, translate terms like BULLISH to "صاعد", BEARISH to "هابط", NEUTRAL to "عرضي", APPROVED to "مقبول", REJECTED to "مرفوض", and translate pattern names like "Double Top" to "قمة مزدوجة".

{{
  "mtf_agent": {{
    "daily_trend": "BULLISH / BEARISH / NEUTRAL (Translated to {lang_instruction})",
    "h4_trend": "BULLISH / BEARISH / NEUTRAL (Translated)",
    "trend_strength": 8,
    "permission_to_trade": true
  }},
  "volume_liquidity_agent": {{
    "liquidity_score": 7,
    "smart_money_zones": ["Price level 1", "Price level 2"],
    "fakeout_detected": false
  }},
  "pattern_recognition_agent": {{
    "detected_patterns": ["Pattern Name (Translated)"],
    "pattern_confidence": 85
  }},
  "sentiment_agent": {{
    "overall_sentiment": "BULLISH / BEARISH / NEUTRAL (Translated)",
    "sentiment_score": 6,
    "breaking_news_alert": "None / Alert details...",
    "market_fear_greed": 65
  }},
  "risk_agent": {{
    "status": "APPROVED / REJECTED",
    "reason": "...",
    "sl_price": 0.0,
    "tp1": 0.0,
    "tp2": 0.0,
    "tp3": 0.0
  }},
  "execution_agent": {{
    "action": "BUY / SELL / HOLD",
    "symbol": "{symbol}",
    "lot_size": 0.0,
    "entry_price": 0.0,
    "sl": 0.0,
    "tp": 0.0
  }},
  "strategist_agent": {{
    "Action": "BUY / SELL / HOLD",
    "Confidence_Score": 85,
    "Chain_of_Thought": "...",
    "Execution_Summary": "..."
  }}
}}
"""

def chat_with_omni_ai(messages, context, lang="ar"):
    api_key = os.getenv("GITHUB_TOKEN")
    if not api_key:
        return "⚠️ رمز GitHub (GITHUB_TOKEN) غير موجود. يرجى إضافته في القائمة الجانبية للدردشة مع المستشار." if lang == "ar" else "⚠️ GitHub Token is missing."

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

    url = "https://models.inference.ai.azure.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o", # use gpt-4o for smart chat
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
    """
    Sends all data in one payload to get the entire ecosystem analysis instantly using GitHub Models.
    """
    api_key = os.getenv("GITHUB_TOKEN")
    if not api_key:
        logger.error("GITHUB_TOKEN is not set.")
        err = "لم تقم بإدخال رمز GitHub (GITHUB_TOKEN) في القائمة الجانبية." if lang == "ar" else "GitHub Token is missing from the sidebar."
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
    url = "https://models.inference.ai.azure.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Using gpt-4o-mini via GitHub Models (Free and fast for JSON output)
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": get_omni_system_prompt(symbol, lang, supports, resistances, chat_context)},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Sending Omni-Data to GitHub Models API for {symbol}...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
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
            err_msg = f"Network error calling GitHub Models API: {e}"
            if hasattr(e, 'response') and e.response is not None:
                err_msg += f"\nResponse: {e.response.text}"
            logger.error(err_msg)
            if attempt == max_retries - 1:
                return None, err_msg
            time.sleep(base_delay)
        except (json.JSONDecodeError, KeyError) as e:
            text_val = locals().get('model_text', 'Not available (KeyError before assignment)')
            err_msg = f"Error parsing model response: {e}\nResponse text: {text_val}"
            logger.error(err_msg)
            return None, err_msg
            
    return None, "Unknown Error"
