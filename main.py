import logging
from data_fetcher import get_xauusd_data, get_account_balance, get_daily_atr
from macro_fetcher import fetch_all_macro_data
from agent import get_technical_analysis, get_macro_analysis, get_risk_management_analysis, get_strategist_analysis
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def format_data_for_prompt(df):
    """
    Formats the pandas DataFrame into a string summary that can be read by the LLM.
    We take only the last N candles to prevent exceeding context limits while 
    maintaining enough recent context for technical analysis.
    """
    if df is None or df.empty:
        return "No data available."
    
    # Take the last 20 candles for the prompt
    recent_data = df.tail(20).copy()
    # Format times to string
    recent_data['time'] = recent_data['time'].dt.strftime('%Y-%m-%d %H:%M')
    
    # Convert to a readable string format
    summary = ""
    for _, row in recent_data.iterrows():
        summary += f"[{row['time']}] O:{row['open']:.2f} H:{row['high']:.2f} L:{row['low']:.2f} C:{row['close']:.2f} "
        summary += f"| RSI:{row.get('RSI_14', 0):.2f} "
        summary += f"| MACD:{row.get('MACD_12_26_9', 0):.2f} Hist:{row.get('MACDh_12_26_9', 0):.2f} "
        summary += f"| ATR:{row.get('ATRr_14', 0):.2f}\n"
    return summary

def main():
    logger.info("Starting Technical Analysis Process for XAUUSD...")
    
    # 1. Fetch Data
    logger.info("Fetching H4 Data...")
    h4_df = get_xauusd_data('H4', num_candles=100)
    
    logger.info("Fetching H1 Data...")
    h1_df = get_xauusd_data('H1', num_candles=100)
    
    if h4_df is None or h1_df is None:
        logger.error("Could not retrieve data from MT5. Ensure MT5 is running and logged in on this machine.")
        logger.info("Alternatively, we can modify this script to accept webhook data later.")
        return
        
    h4_summary = format_data_for_prompt(h4_df)
    h1_summary = format_data_for_prompt(h1_df)
    
    # 2. Fetch Macro Data
    logger.info("Fetching Fundamental Macro Data...")
    macro_summary = fetch_all_macro_data()
    
    # 3. Analyze using AI
    logger.info("Calling Lead Technical Analysis Agent...")
    tech_analysis_json = get_technical_analysis(h1_summary, h4_summary)
    
    logger.info("Calling Chief Fundamental Macro Agent...")
    macro_analysis_json = get_macro_analysis(macro_summary)
    
    print("\n" + "="*50)
    if tech_analysis_json:
        logger.info("Technical Analysis Complete!")
        print("--- Technical Agent JSON Output ---")
        print(json.dumps(tech_analysis_json, indent=4, ensure_ascii=False))
        
        # 4. Risk Management Analysis
        entry_price = tech_analysis_json.get("suggested_entry_price")
        sl_price = tech_analysis_json.get("suggested_stop_loss")
        
        if entry_price and sl_price:
            logger.info("Fetching Account Balance and Daily ATR for Risk Management...")
            balance = get_account_balance()
            daily_atr = get_daily_atr()
            
            logger.info("Calling Risk Management Agent...")
            risk_analysis_json = get_risk_management_analysis(balance, entry_price, sl_price, daily_atr)
            
            print("-" * 50)
            if risk_analysis_json:
                logger.info("Risk Management Analysis Complete!")
                print("--- Risk Agent JSON Output ---")
                print(json.dumps(risk_analysis_json, indent=4, ensure_ascii=False))
            else:
                logger.error("Failed to get analysis from Risk Agent.")
        else:
            logger.warning("Technical Agent did not provide suggested entry or stop loss. Skipping Risk Agent.")
            
    else:
        logger.error("Failed to get analysis from Technical Agent.")
        
    print("-" * 50)
    
    if macro_analysis_json:
        logger.info("Macro Analysis Complete!")
        print("--- Macro Agent JSON Output ---")
        print(json.dumps(macro_analysis_json, indent=4, ensure_ascii=False))
    else:
        logger.error("Failed to get analysis from Macro Agent.")
        
    print("-" * 50)
    
    # 5. Chief Trading Strategist Analysis
    if tech_analysis_json and macro_analysis_json and risk_analysis_json:
        logger.info("Calling Chief Trading Strategist...")
        strategist_json = get_strategist_analysis(tech_analysis_json, macro_analysis_json, risk_analysis_json)
        
        if strategist_json:
            logger.info("Strategist Analysis Complete!")
            print("--- CHIEF TRADING STRATEGIST: FINAL DECISION ---")
            print(json.dumps(strategist_json, indent=4, ensure_ascii=False))
        else:
            logger.error("Failed to get analysis from Strategist Agent.")
    else:
        logger.error("Cannot call Strategist Agent: Missing one or more reports.")
        
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
