import telebot
import yaml
import socket
import struct
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('UDPAttackBot')

@dataclass
class AttackConfig:
    target_ip: str
    target_port: int
    packet_size: int
    duration_seconds: int

@dataclass
class AttackStatus:
    is_active: bool
    start_time: Optional[datetime]
    packets_sent: int
    packets_received: int
    bytes_transferred: int

class UDPAttackBot:
    def __init__(self, token: str, config_path: str = 'config.yaml'):
        self.token = token
        self.bot = telebot.TeleBot(token)
        self.config = self._load_config(config_path)
        self.attack_status = AttackStatus(
            is_active=False,
            start_time=None,
            packets_sent=0,
            packets_received=0,
            bytes_transferred=0
        )
        self.current_config: Optional[AttackConfig] = None
        self._register_commands()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Configuration file {config_path} not found")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            return {}

    def _register_commands(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            welcome_text = (
                f"*{self.config.get('bot', {}).get('name', 'UDP Attack Monitor')}*\n\n"
                "Available commands:\n"
                "/start_attack - Initiate UDP attack simulation\n"
                "/stop_attack - Stop current attack session\n"
                "/status - View attack status and statistics\n"
                "/config - Configure IP and port settings\n"
            )
            self.bot.reply(message, welcome_text, parse_mode='Markdown')

        @self.bot.message_handler(commands=['start_attack'])
        def start_attack(message):
            if self.attack_status.is_active:
                self.bot.reply(message, "⚠️ An attack session is already in progress.", parse_mode='Markdown')
                return

            config_message = (
                "Please enter the target IP address:\n"
                f"(Default: {self.config.get('attack_settings', {}).get('default_port', 53)})"
            )
            self.bot.reply(message, config_message)
            self.bot.register_next_step_handler(message, self._get_attack_ip)

        def _get_attack_ip(message):
            try:
                target_ip = message.text.strip()
                socket.inet_aton(target_ip)

                port_message = "Please enter the target port number:"
                self.bot.reply(message, port_message)
                self.bot.register_next_step_handler(message, lambda m: self._get_attack_port(m, target_ip))
            except socket.error:
                self.bot.reply(message, "❌ Invalid IP address. Please try again.")

        def _get_attack_port(message, target_ip: str):
            try:
                target_port = int(message.text.strip())
                if not 1 <= target_port <= 65535:
                    raise ValueError("Port must be between 1 and 65535")

                self.current_config = AttackConfig(
                    target_ip=target_ip,
                    target_port=target_port,
                    packet_size=self.config.get('attack_settings', {}).get('max_packet_size', 1500),
                    duration_seconds=60
                )

                self._initiate_attack()
            except ValueError:
                self.bot.reply(message, "❌ Invalid port number. Please enter a valid port (1-65535).")

        @self.bot.message_handler(commands=['stop_attack'])
        def stop_attack(message):
            if not self.attack_status.is_active:
                self.bot.reply(message, "ℹ️ No active attack session to stop.", parse_mode='Markdown')
                return

            self._terminate_attack()
            stop_text = (
                f"✅ Attack session stopped successfully!\n\n"
                f"Duration: {self.attack_status.start_time.strftime('%H:%M:%S')}\n"
                f"Packets sent: {self.attack_status.packets_sent}\n"
                f"Packets received: {self.attack_status.packets_received}"
            )
            self.bot.reply(message, stop_text, parse_mode='Markdown')

        @self.bot.message_handler(commands=['status'])
        def show_status(message):
            if not self.attack_status.is_active:
                status_text = "📊 *Attack Status*\n\n⏹️ No active session\n\nUse /start_attack to begin a new attack simulation."
            else:
                start_time = self.attack_status.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.attack_status.start_time else 'N/A'
                status_text = (
                    f"📊 *Attack Status*\n\n"
                    f"🟢 Active Session\n"
                    f"Start Time: {start_time}\n"
                    f"Packets Sent: {self.attack_status.packets_sent}\n"
                    f"Packets Received: {self.attack_status.packets_received}\n"
                    f"Bytes Transferred: {self.attack_status.bytes_transferred / 1024:.2f} KB\n\n"
                    f"Target: {self.current_config.target_ip}:{self.current_config.target_port}" if self.current_config else "No target configured"
                )
            self.bot.reply(message, status_text, parse_mode='Markdown')

        @self.bot.message_handler(commands=['config'])
        def show_config(message):
            attack_settings = self.config.get('attack_settings', {})
            config_text = (
                f"⚙️ *Current Configuration*\n\n"
                f"Default Port: {attack_settings.get('default_port', 53)}\n"
                f"Max Packet Size: {attack_settings.get('max_packet_size', 1500)} bytes\n"
                f"Detection Threshold: {attack_settings.get('detection_threshold', 100)}\n"
                f"Response Time: {attack_settings.get('response_time_ms', 500)} ms\n\n"
                f"Enabled Ports:\n" +
                "\n".join([f"  • {port}" for port in self.config.get('udp_config', {}).get('enabled_ports', [])])
            )
            self.bot.reply(message, config_text, parse_mode='Markdown')

        @self.bot.message_handler(func=lambda m: True)
        def handle_default(message):
            default_text = (
                "ℹ️ Command not recognized. Available commands:\n"
                "/start_attack - Initiate UDP attack\n"
                "/stop_attack - Stop attack session\n"
                "/status - View status\n"
                "/config - View configuration\n"
                "/help - Show help menu"
            )
            self.bot.reply(message, default_text, parse_mode='Markdown')

    def _initiate_attack(self):
        self.attack_status = AttackStatus(
            is_active=True,
            start_time=datetime.now(),
            packets_sent=0,
            packets_received=0,
            bytes_transferred=0
        )

        attack_start_text = (
            f"🚀 *UDP Attack Initiated*\n\n"
            f"Target IP: {self.current_config.target_ip}\n"
            f"Target Port: {self.current_config.target_port}\n"
            f"Packet Size: {self.current_config.packet_size} bytes\n"
            f"Start Time: {self.attack_status.start_time.strftime('%H:%M:%S')}"
        )

    def _terminate_attack(self):
        self.attack_status.is_active = False
        end_time = datetime.now()
        if self.attack_status.start_time:
            duration = end_time - self.attack_status.start_time
            logger.info(f"Attack session terminated. Duration: {duration}")

    def _send_udp_packet(self, ip: str, port: int, data: bytes) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            sock.sendto(data, (ip, port))
            self.attack_status.packets_sent += 1
            self.attack_status.bytes_transferred += len(data)
            return True
        except socket.error as e:
            logger.error(f"UDP packet transmission error: {e}")
            return False

    def _create_attack_packet(self, sequence: int) -> bytes:
        header = struct.pack('!IH', sequence, self.current_config.packet_size if self.current_config else 1500)
        timestamp = int(time.time() * 1000)
        payload = struct.pack('!I', timestamp) + b'UDP_ATTACK'
        return header + payload

    def run(self):
        logger.info("Starting Telegram UDP Attack Bot...")
        self.bot.infinity_polling()

def main():
    import os

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set")
        return

    bot = UDPAttackBot(token)
    bot.run()

if __name__ == '__main__':
    main()
  
