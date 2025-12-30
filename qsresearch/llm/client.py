"""
Groq LLM Client
Wrapper around the Groq API (via OpenAI SDK) for the Quant Hedge Fund system.
"""

from typing import Optional, Dict, Any, List
import json
import os
from loguru import logger
from openai import OpenAI

class GroqClient:
    """Client for interacting with Groq's LLM API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the Groq client.

        Args:
            api_key: Groq API key (defaults to env var GROQ_API_KEY)
            model: Model name (defaults to env var GROQ_MODEL)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

        if not self.api_key:
            logger.warning("GROQ_API_KEY not set. LLM features will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=self.api_key,
            )
            logger.info(f"Groq Client initialized with model: {self.model}")

    def generate_completion(
        self, 
        system_prompt: str, 
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False
    ) -> str:
        """
        Generate a completion from the LLM.

        Args:
            system_prompt: The system instruction.
            user_prompt: The user query.
            temperature: Creativity (0.0 to 1.0).
            max_tokens: Max output tokens.
            json_mode: Whether to enforce JSON output.

        Returns:
            The raw text response.
        """
        if not self.client:
            raise ValueError("Groq Client not initialized (missing API key)")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            raise

    def generate_strategy_params(self, market_regime: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized method to generate strategy parameters from a regime dict.
        """
        system_prompt = """
        You are an expert Quantitative Researcher assistant.
        Your goal is to analyze market regime metrics and suggest optimal parameters for a Factor-based strategy.
        
        The strategy has these tunable parameters:
        - top_n: Number of stocks to hold (10-50)
        - momentum_window: Tuple of (fast_period, slow_period)
        - rebalance_frequency: 'month_end' or 'quarter_end'
        - factor_weights: Dict of {'momentum': float, 'value': float, 'quality': float} (must sum to 1.0)
        
        Output ONLY valid JSON.
        """
        
        regime_str = json.dumps(market_regime, indent=2)
        user_prompt = f"""
        Current Market Regime Metrics:
        {regime_str}
        
        Based on these metrics, suggest the optimal strategy configuration.
        Explain your reasoning in a 'reasoning' field, but ensure the 'config' field contains the parameters.
        """
        
        response = self.generate_completion(
            system_prompt, 
            user_prompt, 
            temperature=0.2, 
            json_mode=True
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {response}")
            raise
