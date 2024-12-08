import pyshark
import openai
import time
import json
from datetime import datetime
from collections import defaultdict
import asyncio
import aiohttp
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PoetryStyle(Enum):
    PESSOA = "pessoa"
    WHITMAN = "whitman"
    DICKINSON = "dickinson"

@dataclass
class PacketData:
    src_ip: str
    dest_ip: str
    protocol: str
    length: int
    timestamp: float
    port_src: Optional[int] = None
    port_dst: Optional[int] = None
    flags: Optional[str] = None

class NetworkPoetryGenerator:
    def __init__(self, interface: str, openai_api_key: str):
        self.interface = interface
        self.capture = pyshark.LiveCapture(interface=interface)
        self.openai_client = openai.Client(api_key=openai_api_key)
        self.packet_buffer: List[PacketData] = []
        self.poetry_archive: Dict[str, List[str]] = defaultdict(list)
        
    def extract_packet_data(self, packet) -> PacketData:
        """Extract relevant data from a packet."""
        try:
            return PacketData(
                src_ip=packet.ip.src if hasattr(packet, 'ip') else "Unknown",
                dest_ip=packet.ip.dst if hasattr(packet, 'ip') else "Unknown",
                protocol=packet.transport_layer if hasattr(packet, 'transport_layer') else "Unknown",
                length=int(packet.length),
                timestamp=time.time(),
                port_src=int(packet[packet.transport_layer].srcport) if hasattr(packet, 'transport_layer') else None,
                port_dst=int(packet[packet.transport_layer].dstport) if hasattr(packet, 'transport_layer') else None,
                flags=packet[packet.transport_layer].flags if hasattr(packet, 'transport_layer') else None
            )
        except Exception as e:
            logger.error(f"Error extracting packet data: {e}")
            return None

    def craft_prompt(self, packets: List[PacketData], style: PoetryStyle) -> str:
        """Create a poetic prompt based on accumulated packet data."""
        base_context = {
            PoetryStyle.PESSOA: """
            Channel the introspective, philosophical voice of Fernando Pessoa's heteronyms.
            Consider each packet as a fragment of consciousness traversing the digital realm.
            Reflect on the metaphysical implications of data transfer and digital existence.
            """,
            PoetryStyle.WHITMAN: """
            Embrace Walt Whitman's expansive, celebratory style.
            See each packet as part of the grand symphony of modern life.
            Connect the digital flow to the universal human experience.
            """,
            PoetryStyle.DICKINSON: """
            Apply Emily Dickinson's concise, profound observations.
            Find deep meaning in the precise moments of packet transmission.
            Use dashes and unconventional capitalization to emphasize digital rhythms.
            """
        }

        packet_descriptions = []
        for packet in packets:
            description = (
                f"Data flows from {packet.src_ip}:{packet.port_src} to "
                f"{packet.dest_ip}:{packet.port_dst}, "
                f"carrying {packet.length} bytes through {packet.protocol}"
            )
            packet_descriptions.append(description)

        return f"""
        {base_context[style]}
        
        Consider these network movements:
        {chr(10).join(packet_descriptions)}
        
        Transform these digital exchanges into a poetic reflection that captures
        their essential nature while maintaining the characteristic style.
        Include metaphysical observations about the nature of digital consciousness
        and the symbolic meaning of these electronic transmissions.
        """

    async def generate_poetry(self, prompt: str) -> str:
        """Generate poetic text using OpenAI's API."""
        try:
            response = await asyncio.to_thread(
                lambda: self.openai_client.completions.create(
                    model="gpt-4",
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.9
                )
            )
            return response.choices[0].text.strip()
        except Exception as e:
            logger.error(f"Error generating poetry: {e}")
            return "Error generating poetic response"

    async def process_packets(self, style: PoetryStyle = PoetryStyle.PESSOA):
        """Main packet processing loop."""
        async def buffer_processor():
            while True:
                if len(self.packet_buffer) >= 5:
                    prompt = self.craft_prompt(self.packet_buffer, style)
                    poetry = await self.generate_poetry(prompt)
                    
                    # Archive the poetry with timestamp
                    timestamp = datetime.now().isoformat()
                    self.poetry_archive[timestamp] = {
                        'poetry': poetry,
                        'packets': [vars(p) for p in self.packet_buffer],
                        'style': style.value
                    }
                    
                    # Clear buffer
                    self.packet_buffer.clear()
                    
                    # Log and display the poetry
                    logger.info(f"\n--- New Poetry Generated at {timestamp} ---\n{poetry}\n")
                    
                await asyncio.sleep(1)

        # Start the buffer processor
        buffer_processor_task = asyncio.create_task(buffer_processor())

        # Packet capture loop
        try:
            for packet in self.capture.sniff_continuously():
                packet_data = self.extract_packet_data(packet)
                if packet_data:
                    self.packet_buffer.append(packet_data)
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Stopping packet capture...")
            buffer_processor_task.cancel()
        finally:
            # Save archive to file
            self.save_archive()

    def save_archive(self):
        """Save the poetry archive to a JSON file."""
        try:
            with open('network_poetry_archive.json', 'w') as f:
                json.dump(self.poetry_archive, f, indent=2)
            logger.info("Poetry archive saved successfully")
        except Exception as e:
            logger.error(f"Error saving poetry archive: {e}")

async def main():
    generator = NetworkPoetryGenerator(
        interface='eth0',
        openai_api_key="YOUR_OPENAI_API_KEY"
    )
    await generator.process_packets()

if __name__ == "__main__":
    asyncio.run(main())
