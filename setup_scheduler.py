#!/usr/bin/env python
"""
Scheduler Setup Script

This script helps set up the scheduler system for Swiss Asset Manager.
It creates necessary directories, configuration files, and initializes the scheduler.
"""

import os
import sys
import argparse
import shutil
import subprocess
import platform
from dotenv import load_dotenv

def create_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    else:
        print(f"Directory already exists: {path}")

def create_env_file():
    """Create .env file if it doesn't exist."""
    if not os.path.exists('.env'):
        print("Creating .env file...")
        with open('.env', 'w') as f:
            f.write("""# Swiss Asset Manager Environment Configuration
# Scheduler Settings
SCHEDULER_ENABLED=true
SCHEDULER_USE_PROCESS_MANAGER=true
SCHEDULER_PROCESS_MANAGED=true
SCHEDULER_UPDATE_INTERVAL=60
LOG_LEVEL=INFO

# Update Intervals (minutes)
MARKET_UPDATE_INTERVAL=60
PORTFOLIO_UPDATE_INTERVAL=120
CYCLES_UPDATE_INTERVAL=240
NEWS_UPDATE_INTERVAL=30

# Performance Settings
MAX_PARALLELISM=4
SCHEDULER_PARALLEL_UPDATES=true
SCHEDULER_MAX_WORKERS=4

# API Settings
SCHEDULER_API_ENABLED=true
SCHEDULER_API_PORT=5001

# Advanced Settings
MAX_RESTART_ATTEMPTS=5
GRACEFUL_SHUTDOWN_TIMEOUT=30
SCHEDULER_HEALTH_CHECK_INTERVAL=60
""")
        print("Created .env file with default configuration")
    else:
        print(".env file already exists")

def setup_supervisor():
    """Set up supervisor configuration."""
    supervisor_dir = '/etc/supervisor/conf.d' if platform.system() != 'Darwin' else '/usr/local/etc/supervisor.d'
    
    # Check if supervisor is installed
    try:
        subprocess.run(['which', 'supervisord'], check=True, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Supervisor not found. Please install supervisor first.")
        print("On Ubuntu/Debian: sudo apt-get install supervisor")
        print("On macOS: brew install supervisor")
        return False
    
    # Create supervisor configuration directory if it doesn't exist
    if not os.path.exists(supervisor_dir):
        try:
            os.makedirs(supervisor_dir)
            print(f"Created supervisor config directory: {supervisor_dir}")
        except PermissionError:
            print(f"Permission denied when creating {supervisor_dir}")
            print(f"Please run with sudo or manually create the directory")
            return False
    
    # Copy supervisor config
    config_file = os.path.join(supervisor_dir, 'swiss_asset_manager.conf')
    if os.path.exists('supervisord.conf'):
        try:
            shutil.copy('supervisord.conf', config_file)
            print(f"Copied supervisord.conf to {config_file}")
        except PermissionError:
            print("Permission denied when copying supervisor config")
            print(f"Please manually copy supervisord.conf to {config_file}")
            return False
    else:
        print("supervisord.conf not found. Please create it first.")
        return False
    
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    dependencies = [
        ('python-dotenv', 'dotenv'),
        ('supervisor', 'supervisor'),
        ('flask', 'flask'),
        ('psutil', 'psutil'),
        ('schedule', 'schedule')
    ]
    
    missing = []
    for package, import_name in dependencies:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("Missing dependencies:")
        for package in missing:
            print(f"  - {package}")
        print("\nPlease install them with:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    print("All required dependencies are installed.")
    return True

def create_directories():
    """Create necessary directories."""
    directories = ['logs', 'temp', 'data']
    for directory in directories:
        create_directory(directory)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Set up Swiss Asset Manager Scheduler')
    parser.add_argument('--supervisor', action='store_true', help='Set up supervisor configuration')
    parser.add_argument('--check', action='store_true', help='Check dependencies only')
    parser.add_argument('--env', action='store_true', help='Create .env file only')
    args = parser.parse_args()
    
    print("Swiss Asset Manager - Scheduler Setup")
    print("====================================")
    
    if args.check:
        check_dependencies()
        return
    
    if args.env:
        create_env_file()
        return
    
    if args.supervisor:
        setup_supervisor()
        return
    
    # Full setup
    if not check_dependencies():
        return
    
    create_directories()
    create_env_file()
    
    if setup_supervisor():
        print("\nSetup completed successfully!")
        print("\nNext steps:")
        print("1. Edit the .env file to configure the scheduler")
        print("2. Start the services with: sudo supervisorctl reread && sudo supervisorctl update")
        print("3. Check status with: sudo supervisorctl status")
    else:
        print("\nSetup incomplete. Please check the errors above.")

if __name__ == '__main__':
    main()