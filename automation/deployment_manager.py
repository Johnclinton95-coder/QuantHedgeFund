"""
Model Serving - Deployment Management

Handles model deployment and serving configuration.
Based on the Quant Science production deployment architecture.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json

from loguru import logger

from config.settings import get_settings


class DeploymentManager:
    """
    Manages model deployment state and configuration.
    
    Tracks which model version is currently deployed to production
    and handles promotion of new models.
    """
    
    def __init__(self, deployment_dir: Optional[Path] = None):
        """
        Initialize deployment manager.
        
        Args:
            deployment_dir: Directory for deployment state files
        """
        settings = get_settings()
        self.deployment_dir = deployment_dir or settings.dashboard_data_dir / "model_serving"
        self.deployment_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.deployment_dir / "deployment_state.json"
        self._state: Optional[Dict[str, Any]] = None
        
        logger.info(f"Deployment manager initialized: {self.deployment_dir}")
    
    def get_current_deployment(self) -> Dict[str, Any]:
        """
        Get the current deployment state.
        
        Returns:
            Dictionary with deployment information
        """
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        
        return {
            "status": "not_deployed",
            "message": "No model currently deployed",
        }
    
    def deploy_model(
        self,
        run_id: str,
        alias: str = "live-trading",
        artifact_uri: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Deploy a model to production.
        
        Args:
            run_id: MLflow run ID to deploy
            alias: Deployment alias (e.g., "live-trading", "staging")
            artifact_uri: Path to model artifacts
            metrics: Model performance metrics
            
        Returns:
            Deployment state dictionary
        """
        deployment_state = {
            "run_id": run_id,
            "alias": alias,
            "deployed_at": datetime.now().isoformat(),
            "artifact_uri": artifact_uri or f"mlartifacts/{run_id}",
            "status": "deployed",
            "metrics": metrics or {},
            "version": f"production-model:v{datetime.now().strftime('%Y%m%d')}-alias-{alias}",
        }
        
        # Save deployment state
        with open(self.state_file, "w") as f:
            json.dump(deployment_state, f, indent=2)
        
        # Also save versioned backup
        backup_file = self.deployment_dir / f"deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, "w") as f:
            json.dump(deployment_state, f, indent=2)
        
        logger.info(f"Deployed model {run_id} with alias {alias}")
        
        self._state = deployment_state
        return deployment_state
    
    def get_deployed_model_info(self) -> Dict[str, Any]:
        """
        Get information about the currently deployed model.
        
        Returns:
            Dictionary with model details for dashboard display
        """
        state = self.get_current_deployment()
        
        if state.get("status") != "deployed":
            return state
        
        return {
            "run_id": state.get("run_id", ""),
            "alias": state.get("alias", ""),
            "version": state.get("version", ""),
            "deployed_at": state.get("deployed_at", ""),
            "artifact_uri": state.get("artifact_uri", ""),
            "metrics": state.get("metrics", {}),
        }
    
    def rollback(self, to_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Rollback to a previous deployment.
        
        Args:
            to_version: Specific version to rollback to (latest if None)
            
        Returns:
            New deployment state
        """
        # Find previous deployments
        backups = sorted(self.deployment_dir.glob("deployment_*.json"), reverse=True)
        
        if len(backups) < 2:
            return {"error": "No previous deployment to rollback to"}
        
        # Load previous deployment
        previous_file = backups[1]  # Skip current, get previous
        with open(previous_file) as f:
            previous_state = json.load(f)
        
        # Restore it as current
        previous_state["rollback_from"] = self.get_current_deployment().get("run_id")
        previous_state["rollback_at"] = datetime.now().isoformat()
        
        with open(self.state_file, "w") as f:
            json.dump(previous_state, f, indent=2)
        
        logger.info(f"Rolled back to deployment: {previous_state.get('run_id')}")
        
        return previous_state


def get_deployment_manager() -> DeploymentManager:
    """Get the singleton deployment manager instance."""
    return DeploymentManager()
