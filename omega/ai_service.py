import os
import json
from openai import OpenAI
from groq import Groq
from loguru import logger
from typing import Dict, Any, Optional

class MarketAnalyst:
    """
    AI-powered market analysis engine using Groq (LPU Inference).
    Transforms structured market data into governance-safe trading insights.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # Prioritize Groq as requested by user
        self.groq_key = os.getenv("GROK_API_KEY")
        self.client = Groq(api_key=self.groq_key)
        self.model = "llama-3.3-70b-versatile" # Updated to new supported model
        logger.info("🧠 Initializing AI Service with Groq (Llama3-70b)")
            
    def generate_market_summary(self, symbol: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Feature 1: AI Market Summary"""
        prompt = f"""
        You are a professional trading assistant.
        Analyze this market snapshot and produce:
        1. A 1-2 sentence market summary
        2. Bias: BULLISH / BEARISH / NEUTRAL
        3. Confidence score (0-100)

        Rules:
        - Do NOT predict future prices
        - Focus on momentum, volume, and context
        
        Snapshot: {json.dumps(snapshot)}
        """
        return self._call_grok(prompt)

    def detect_regime(self, symbol: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Feature 2: AI Market Regime Detection"""
        prompt = f"""
        Classify the current market regime for {symbol}.
        Choose ONE: [TREND, RANGE, BREAKOUT, HIGH_VOLATILITY, LOW_LIQUIDITY]
        Return JSON with: regime, confidence, reason.
        
        Snapshot: {json.dumps(snapshot)}
        """
        return self._call_grok(prompt)

    def check_risk_guardrail(self, symbol: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Feature 3: AI Risk Guardrail"""
        prompt = f"""
        Evaluate trade safety for {symbol}.
        Consider: Spread, Liquidity, Volatility, Session.
        Return JSON with: 
        - risk_level: LOW / MEDIUM / HIGH
        - explanation: 1 sentence reason
        
        Snapshot: {json.dumps(snapshot)}
        """
        return self._call_grok(prompt)

    def suggest_trade_levels(self, symbol: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Feature 4: AI Stop-Loss & Take-Profit"""
        prompt = f"""
        Suggest stop-loss and take-profit levels for {symbol}.
        Rules:
        - Use ATR, VWAP distance, and volatility
        - Risk-reward between 1:1.5 and 1:3
        - No price prediction language
        
        Return JSON with: stop_loss, take_profit, risk_reward, reason
        
        Snapshot: {json.dumps(snapshot)}
        """
        return self._call_grok(prompt)

    def _call_grok(self, user_prompt: str) -> Dict[str, Any]:
        """Internal helper to call Grok safely"""
        if not self.client:
            return {"error": "AI Service Disabled"}
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a specialized trading AI. Output strictly valid JSON."},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,
                max_tokens=512,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Grok Call Failed: {e}")
            return {"error": str(e)}

# Singleton instance
_ANALYST = None

def get_market_analyst(force_refresh=False):
    global _ANALYST
    if _ANALYST is None or force_refresh:
        logger.info("🔄 Refreshing AI Service Instance")
        _ANALYST = MarketAnalyst()
    return _ANALYST
