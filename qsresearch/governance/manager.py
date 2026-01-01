"""
QS Governance Manager
Handles strategy lifecycle, audit logs, and safety gates.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger
from pathlib import Path

class GovernanceManager:
    """Manages the governance and audit trail for trading strategies."""

    def __init__(self, db_manager):
        self.db = db_manager

    def generate_config_hash(self, config: Dict[str, Any]) -> str:
        """Generate a unique SHA256 hash for a strategy configuration."""
        # Sort keys to ensure consistent hashing
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def log_strategy_approval(
        self,
        config: Dict[str, Any],
        regime_snapshot: Dict[str, Any],
        llm_reasoning: str,
        human_rationale: str,
        approved_by: str,
        stage: str = "SHADOW",
        ttl_days: int = 30,
        mlflow_run_id: Optional[str] = None
    ) -> str:
        """Log a newly approved strategy to the audit trail."""
        strat_hash = self.generate_config_hash(config)
        ttl_expiry = datetime.now() + timedelta(days=ttl_days)
        
        sql = """
            INSERT OR REPLACE INTO strategy_audit_log 
            (strategy_hash, config_json, regime_snapshot, llm_reasoning, human_rationale, approved_by, stage, ttl_expiry, mlflow_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            strat_hash, 
            json.dumps(config), 
            json.dumps(regime_snapshot), 
            llm_reasoning, 
            human_rationale, 
            approved_by, 
            stage, 
            ttl_expiry,
            mlflow_run_id
        )
        self.db.execute(sql, params)
        
        logger.info(f"Strategy {strat_hash[:8]} logged in stage {stage} by {approved_by}")
        return strat_hash

    def get_active_strategy(self) -> Optional[Dict[str, Any]]:
        """Retrieve the currently active strategy (highest stage)."""
        sql = """
            SELECT config_json, strategy_hash, stage, ttl_expiry 
            FROM strategy_audit_log 
            WHERE stage IN ('CANARY', 'FULL') 
            AND ttl_expiry > CURRENT_TIMESTAMP
            ORDER BY approved_at DESC LIMIT 1
        """
        result_df = self.db.query(sql)
        
        if not result_df.is_empty():
            row = result_df.row(0)
            config = json.loads(row[0])
            config["strategy_hash"] = row[1]
            config["stage"] = row[2]
            config["ttl_expiry"] = row[3]
            return config
        return None

    def promote_strategy(self, strat_hash: str, next_stage: str, approved_by: str):
        """Promote a strategy to the next stage in the deployment ladder."""
        valid_stages = ["SHADOW", "PAPER", "CANARY", "FULL"]
        if next_stage not in valid_stages:
            raise ValueError(f"Invalid stage: {next_stage}")
            
        sql = """
            UPDATE strategy_audit_log 
            SET stage = ?, approved_by = ?, approved_at = CURRENT_TIMESTAMP
            WHERE strategy_hash = ?
        """
        self.db.execute(sql, (next_stage, approved_by, strat_hash))
        
        logger.info(f"Strategy {strat_hash[:8]} promoted to {next_stage} by {approved_by}")

    def log_drift(self, strat_hash: str, metric: str, expected: float, actual: float):
        """Log a drift metric for a strategy."""
        drift_score = abs(actual - expected) / (abs(expected) + 1e-9)
        status = "GREEN"
        if drift_score > 0.5: status = "RED"
        elif drift_score > 0.2: status = "YELLOW"
        
        sql = """
            INSERT INTO strategy_drift_logs (strategy_hash, metric_name, expected_value, actual_value, drift_score, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, (strat_hash, metric, expected, actual, drift_score, status))
        
        if status == "RED":
            logger.error(f"CRITICAL DRIFT: Strategy {strat_hash[:8]} {metric} has drift score {drift_score:.2f}")
            # Here we would trigger an auto-halt in a real system
