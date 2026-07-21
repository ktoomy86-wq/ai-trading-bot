import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to initialize Firebase
_db = None

def init_firebase():
    global _db
    if _db is not None:
        return _db
        
    try:
        # Check if already initialized
        firebase_admin.get_app()
        _db = firestore.client()
        return _db
    except ValueError:
        pass # App not initialized yet
        
    key_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
    
    try:
        import streamlit as st
        if "firebase" in st.secrets:
            # Running in Streamlit Cloud with secrets
            cred_dict = dict(st.secrets["firebase"])
            # Remove any specific metadata st.secrets might add
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _db = firestore.client()
            logger.info("Firebase initialized successfully from Streamlit Secrets.")
            return _db
    except Exception as e:
        pass # Not running in Streamlit or secrets not found
        
    if not os.path.exists(key_path):
        logger.warning(f"Firebase credentials not found at {key_path} and no st.secrets found. Firebase disabled.")
        return None
        
    try:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        _db = firestore.client()
        logger.info("Firebase initialized successfully from local file.")
        return _db
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return None

def save_trade_analysis(symbol, timeframe, analysis_json):
    """
    Saves the AI analysis and trade action to Firestore.
    """
    db = init_firebase()
    if not db:
        return False, "Firebase is not initialized (missing serviceAccountKey.json)."
        
    try:
        doc_ref = db.collection("trade_analyses").document()
        data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "analysis": analysis_json,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": analysis_json.get("strategist_agent", {}).get("Action", "UNKNOWN")
        }
        doc_ref.set(data)
        return True, "Analysis saved to Firestore successfully."
    except Exception as e:
        logger.error(f"Error saving to Firestore: {e}")
        return False, f"Error saving to Firestore: {e}"

def get_trade_history(limit=50):
    """
    Retrieves the latest trade analyses from Firestore.
    """
    db = init_firebase()
    if not db:
        return []
        
    try:
        docs = db.collection("trade_analyses").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
        history = []
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id
            history.append(d)
        return history
    except Exception as e:
        logger.error(f"Error retrieving history from Firestore: {e}")
        return []
