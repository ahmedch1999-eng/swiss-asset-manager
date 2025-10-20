"""
Metrics collector for the scheduler system.
This module collects and logs performance metrics for the scheduler system.
"""

import os
import json
import time
import psutil
import datetime
import logging
import threading
import functools
from functools import wraps

# Make sure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure metrics logger
metrics_logger = logging.getLogger('scheduler_metrics')
metrics_logger.setLevel(logging.INFO)
metrics_file_handler = logging.FileHandler(os.path.join('logs', 'metrics.log'))
metrics_file_handler.setFormatter(logging.Formatter('%(message)s'))
metrics_logger.addHandler(metrics_file_handler)
metrics_logger.propagate = False  # Don't propagate to root logger

class Metrics:
    """Metrics collector for the scheduler system."""
    
    @staticmethod
    def log_task_execution(task_type):
        """Decorator to log task execution metrics."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = False
                error_message = None
                try:
                    result = func(*args, **kwargs)
                    success = True
                    return result
                except Exception as e:
                    error_message = str(e)
                    raise
                finally:
                    duration = time.time() - start_time
                    Metrics.log_metric(task_type, duration, success, error_message)
            return wrapper
        return decorator
    
    @staticmethod
    def log_metric(task_type, duration, success=True, error=None):
        """Log a performance metric."""
        try:
            # Get CPU and memory usage
            process = psutil.Process(os.getpid())
            cpu_usage = process.cpu_percent(interval=0.1)
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            
            # Create metric data
            metric = {
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'task_type': task_type,
                'duration': round(duration, 3),
                'success': success,
                'cpu_usage': round(cpu_usage, 2),
                'memory_mb': round(memory_usage, 2),
            }
            
            # Add error if present
            if error:
                metric['error'] = error
                
            # Log as JSON
            metrics_logger.info(json.dumps(metric))
        except Exception as e:
            # Fail silently - metrics should never break functionality
            pass
    
    @staticmethod
    def collect_system_metrics():
        """Collect and log system-wide metrics."""
        try:
            # Get system-wide metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Create metric data
            metric = {
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'task_type': 'system_metrics',
                'system_cpu': round(cpu_usage, 2),
                'system_memory_percent': round(memory.percent, 2),
                'system_disk_percent': round(disk.percent, 2),
                'success': True
            }
            
            # Log as JSON
            metrics_logger.info(json.dumps(metric))
        except Exception as e:
            # Fail silently - metrics should never break functionality
            pass

class MetricsCollector:
    """Background metrics collector."""
    
    def __init__(self, interval=60):
        """Initialize the metrics collector.
        
        Args:
            interval: Collection interval in seconds
        """
        self.interval = interval
        self.running = False
        self.thread = None
    
    def start(self):
        """Start collecting metrics."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop collecting metrics."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _run(self):
        """Run the metrics collection loop."""
        while self.running:
            try:
                Metrics.collect_system_metrics()
            except:
                pass  # Fail silently
                
            # Sleep for the specified interval
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)

# Create a global metrics collector
metrics_collector = MetricsCollector()

def init_metrics():
    """Initialize the metrics collector."""
    metrics_collector.start()