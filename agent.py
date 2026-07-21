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

def get_omni_system_prompt(symbol, lang="ar"):
    lang_instruction = "Arabic language" if lang == "ar" else "English language"
    return f"""You are the complete {symbol} AI Trading Ecosystem, consisting of 4 virtual sub-agents:
1. Technical Agent: Analyzes MT5 H4 and H1 data (Support/Resistance, BOS/CHOCH, momentum, trend, entry, SL).
2. Macro Agent: Analyzes fundamental economic data and news for the currencies in {symbol} and DXY.
3. Risk Agent: Validates the trade. Max risk is 1% of account balance. Max SL distance is 1.5x daily ATR. Calculates Lot Size and TP1, TP2, TP3 based on 1:1, 1:2, 1:3 RR.
4. Chief Strategist: Synthesizes everything into a final Action (BUY/SELL/HOLD).

You must output a SINGLE JSON object containing all 4 reports precisely in this format.
IMPORTANT: All string values, explanations, summaries, and reasons inside the JSON MUST be written in the {lang_instruction}.

{{
  "technical_agent": {{
    "support_resistance_zones": ["zone 1...", "zone 2..."],
    "support_resistance_levels": [0.0, 0.0, 0.0],
    "structural_shifts": "...",
    "momentum": "...",
    "current_trend": "...",
    "suggested_entry_price": 0.0,
    "suggested_stop_loss": 0.0,
    "technical_confidence_score": 80
  }},
  "macro_agent": {{
    "fundamental_bias": "Bullish",
    "macro_factors_summary": "...",
    "impact_severity_score": "High",
    "usd_sentiment": "Hawkish"
  }},
  "risk_agent": {{
    "status": "APPROVED",
    "reason": "...",
    "lot_size": 0.0,
    "sl_price": 0.0,
    "tp1": 0.0,
    "tp2": 0.0,
    "tp3": 0.0
  }},
  "strategist_agent": {{
    "Action": "BUY",
    "Entry_Price": 0.0,
    "Confidence_Score": 85,
    "Execution_Summary": "..."
  }}
}}
"""

def get_omni_analysis(symbol: str, h4_data: str, h1_data: str, macro_data: str, balance: float, atr: float, lang="ar"):
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
            {"role": "system", "content": get_omni_system_prompt(symbol, lang)},
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
