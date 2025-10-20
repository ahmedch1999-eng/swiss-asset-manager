"""
Dashboard module for monitoring scheduler health and performance.
This module provides a web-based dashboard for monitoring the scheduler status,
health, and performance metrics.
"""

import os
import json
import time
import datetime
import psutil
import logging
from flask import Blueprint, render_template, jsonify, current_app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join('logs', 'dashboard.log'),
    filemode='a'
)
logger = logging.getLogger('scheduler_dashboard')

# Create Blueprint
scheduler_dashboard = Blueprint('scheduler_dashboard', __name__, 
                              template_folder='templates',
                              static_folder='static')

def get_metrics_history():
    """Get historical metrics data from logs."""
    try:
        metrics_file = os.path.join('logs', 'metrics.log')
        if not os.path.exists(metrics_file):
            return []
        
        with open(metrics_file, 'r') as f:
            lines = f.readlines()
            
        # Parse the last 100 entries
        metrics = []
        for line in lines[-100:]:
            try:
                data = json.loads(line.strip())
                metrics.append(data)
            except json.JSONDecodeError:
                continue
                
        return metrics
    except Exception as e:
        logger.error(f"Error reading metrics history: {str(e)}")
        return []

def get_scheduler_process_info():
    """Get information about the scheduler process."""
    try:
        # Check if scheduler is running
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'scheduler_standalone.py' in ' '.join(proc.info['cmdline'] or []):
                # Get detailed process info
                p = psutil.Process(proc.info['pid'])
                return {
                    'pid': p.pid,
                    'status': p.status(),
                    'cpu_percent': p.cpu_percent(interval=0.1),
                    'memory_percent': p.memory_percent(),
                    'create_time': datetime.datetime.fromtimestamp(p.create_time()).strftime("%Y-%m-%d %H:%M:%S"),
                    'running_time': str(datetime.timedelta(seconds=int(time.time() - p.create_time()))),
                    'threads': len(p.threads()),
                }
        return None
    except Exception as e:
        logger.error(f"Error getting scheduler process info: {str(e)}")
        return None

def get_recent_errors():
    """Get recent errors from the error log."""
    try:
        log_file = os.path.join('logs', 'scheduler_standalone.log')
        if not os.path.exists(log_file):
            return []
            
        with open(log_file, 'r') as f:
            lines = f.readlines()
            
        # Extract error lines
        errors = []
        for line in lines[-200:]:  # Check last 200 lines
            if 'ERROR' in line or 'Exception' in line:
                errors.append(line.strip())
                
        return errors[-10:]  # Return last 10 errors
    except Exception as e:
        logger.error(f"Error getting recent errors: {str(e)}")
        return []

@scheduler_dashboard.route('/dashboard')
def dashboard():
    """Render the dashboard page."""
    try:
        # Get scheduler status from API
        from scheduler_api import get_scheduler_status
        scheduler_status = get_scheduler_status()
        
        # Get process info
        process_info = get_scheduler_process_info()
        
        # Get metrics history
        metrics = get_metrics_history()
        
        # Get recent errors
        errors = get_recent_errors()
        
        # Check if scheduler API is enabled
        scheduler_api_enabled = os.environ.get('SCHEDULER_API_ENABLED', 'false').lower() == 'true'
        
        # Get current configuration
        from scheduler_config import SchedulerConfig
        config = SchedulerConfig.get_current_config()
        
        return render_template(
            'scheduler_dashboard.html',
            scheduler_status=scheduler_status,
            process_info=process_info,
            metrics=metrics,
            errors=errors,
            api_enabled=scheduler_api_enabled,
            config=config
        )
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        return render_template('error.html', error=str(e))

@scheduler_dashboard.route('/api/metrics')
def api_metrics():
    """API endpoint for metrics data."""
    return jsonify(get_metrics_history())

@scheduler_dashboard.route('/api/process')
def api_process():
    """API endpoint for process info."""
    return jsonify(get_scheduler_process_info())

@scheduler_dashboard.route('/api/errors')
def api_errors():
    """API endpoint for recent errors."""
    return jsonify(get_recent_errors())

def init_dashboard(app):
    """Initialize the dashboard with the Flask app."""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Register blueprint
        app.register_blueprint(scheduler_dashboard)
        logger.info("Scheduler dashboard initialized")
    except Exception as e:
        logger.error(f"Failed to initialize dashboard: {str(e)}")