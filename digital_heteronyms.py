#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
# Digital Heteronyms: A Network Traffic Poetry Generator 🌐📝

Where packets pirouette through digital dimensions, transforming binary ballet
into Pessoa's posthumous pixels.

This script—digital_heteronyms.py—transmutes ephemeral data packets into poetic
reflections, channeling the timeless voices of Fernando Pessoa, Walt Whitman,
and Emily Dickinson. Designed for real-time analysis, it:
    - Sniffs network traffic using PyShark
    - Buffers a configurable number of packets
    - Generates AI-powered poetry from OpenAI's GPT models

It's a philosophical probe into the essence of digital existence, where each
TCP handshake becomes a stanza, and every UDP datagram finds its ephemeral verse.
"""

import os
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
from dataclasses import dataclass, field
from enum import Enum

# ------------------------ LEGAL & ETHICAL DISCLAIMER -------------------------
# PessoaNetPackets is an artistic tool that transforms network traffic data
# into poetry using OpenAI's API. By using this script, you acknowledge that:
#
# 1. You comply with all applicable laws and regulations regarding network
#    monitoring, data privacy, and the processing of packet metadata.
# 2. You only capture network traffic on networks you own or are authorized to
#    analyze. Obtain and document necessary permissions.
# 3. You implement anonymization or other privacy protections to safeguard
#    individuals' data in compliance with privacy laws (e.g., GDPR, CCPA).
# 4. You understand that the creator and contributors assume no liability
#    for misuse, and this script is provided "as-is" with no warranties.
#
# For additional guidance, review the expanded disclaimer at the bottom of
# this file, which covers:
#   - Data Privacy & Security
#   - API Usage Compliance (OpenAI)
#   - Ethical Guidelines
#   - Limitation of Liability
#
# The IP addresses (e.g., 192.168.x.x) are fictitious and come from reserved
# private IP ranges (RFC 1918). They are for illustrative purposes only.
# ---------------------------------------------------------------------------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PoetryStyle(Enum):
    """Digital Heteronyms: Each style channels a different literary soul."""
    PESSOA = "pessoa"
    WHITMAN = "whitman"
    DICKINSON = "dickinson"


@dataclass
class PacketData:
    """Metadata for each captured packet."""
    src_ip: str
    dest_ip: str
    protocol: str
    length: int
    timestamp: float
    port_src: Optional[int] = None
    port_dst: Optional[int] = None
    flags: Optional[str] = None


@dataclass
class PoetryArchiveEntry:
    """Archival structure to record generated poems and associated packet data."""
    poetry: str
    packets: List[dict]
    style: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class DigitalHeteronyms:
    """
    # PessoaNetPackets
    Transform your network traffic into philosophical poetry inspired by literary masters.
    Channel the essence of Fernando Pessoa, Walt Whitman, and Emily Dickinson to interpret
    the digital flow of packets in real-time.
    """

    def __init__(
        self,
        interface: str,
        openai_api_key: str,
        buffer_size: int = 5,
        rate_limit_seconds: float = 1.0
    ):
        """
        :param interface: Name of the network interface to sniff (e.g., 'eth0').
        :param openai_api_key: OpenAI API key (retrieved from environment variables).
        :param buffer_size: Number of packets to accumulate before generating a poem.
        :param rate_limit_seconds: Basic rate limit (in seconds) between calls to OpenAI.
        """
        self.interface = interface
        self.buffer_size = buffer_size
        self.rate_limit_seconds = rate_limit_seconds

        # Example BPF filter for high traffic networks: bpf_filter="tcp port 80"
        self.capture = pyshark.LiveCapture(interface=interface)

        self.openai_client = openai.Client(api_key=openai_api_key)
        self.packet_buffer: List[PacketData] = []
        self.poetry_archive: Dict[str, PoetryArchiveEntry] = defaultdict()

        # Basic time-based rate limiting
        self.last_api_call_time = 0.0

    def anonymize_ip(self, ip_address: str) -> str:
        """
        Simple anonymizer that masks part of an IPv4 address to protect privacy.
        192.168.0.101 -> 192.168.x.x
        """
        if ip_address == "Unknown":
            return ip_address
        parts = ip_address.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.x.x"
        return ip_address  # Non-IPv4 or unrecognized format left unchanged

    def extract_packet_data(self, packet) -> Optional[PacketData]:
        """
        Extract relevant metadata from a pyshark packet object.
        Return None if extraction fails (helps with robust exception handling).
        """
        try:
            # Gather IP details
            src_ip = getattr(packet.ip, 'src', "Unknown") if hasattr(packet, 'ip') else "Unknown"
            dest_ip = getattr(packet.ip, 'dst', "Unknown") if hasattr(packet, 'ip') else "Unknown"
            protocol = getattr(packet, 'transport_layer', "Unknown")
            length = int(packet.length)
            timestamp = time.time()

            port_src = None
            port_dst = None
            flags = None

            # If the protocol is recognized, retrieve additional transport info
            if protocol != "Unknown":
                transport_info = getattr(packet, protocol.lower(), None)
                if transport_info:
                    port_src = int(getattr(transport_info, 'srcport', 0))
                    port_dst = int(getattr(transport_info, 'dstport', 0))
                    flags = getattr(transport_info, 'flags', None)

            return PacketData(
                src_ip=self.anonymize_ip(src_ip),
                dest_ip=self.anonymize_ip(dest_ip),
                protocol=protocol,
                length=length,
                timestamp=timestamp,
                port_src=port_src,
                port_dst=port_dst,
                flags=flags
            )
        except Exception as e:
            logger.error(f"Error extracting packet data: {e}")
            return None

    def craft_prompt(self, packets: List[PacketData], style: PoetryStyle) -> str:
        """
        Build the textual prompt for OpenAI, reflecting your chosen poetic lens.
        """
        base_context = {
            PoetryStyle.PESSOA: """
                Channel Fernando Pessoa’s introspective spirit, capturing ephemeral
                digital echoes as existential fragments. Investigate each packet’s
                metaphysical journey across the intangible threshold of cyberspace.
            """,
            PoetryStyle.WHITMAN: """
                Whisper with Walt Whitman’s boundless voice. Embrace each packet as
                part of a cosmic democracy, swirling in a unified tapestry of data
                that hums with the heartbeat of humanity.
            """,
            PoetryStyle.DICKINSON: """
                Adopt Emily Dickinson’s fervent economy of expression. Peer through
                the precise moments of each packet’s birth and flight, sprinkling
                subtle punctuation, dashes, and cryptic wonder throughout.
            """
        }

        # Summarize each packet in a short descriptive line
        packet_descriptions = []
        for packet in packets:
            line = (f"Data from {packet.src_ip}:{packet.port_src} "
                    f"to {packet.dest_ip}:{packet.port_dst}, "
                    f"{packet.length} bytes via {packet.protocol}.")
            packet_descriptions.append(line)

        return f"""
        {base_context[style]}

        Consider the following network transmissions:
        {chr(10).join(packet_descriptions)}

        Weave these ephemeral flows into a poem in the style of {style.value}.
        Highlight each packet's symbolic significance and ephemeral life.
        """

    async def generate_poetry(self, prompt: str) -> str:
        """
        Make an API call to OpenAI, returning the generated text.
        Includes a basic rate limit, sleeping if needed.
        """
        elapsed = time.time() - self.last_api_call_time
        if elapsed < self.rate_limit_seconds:
            await asyncio.sleep(self.rate_limit_seconds - elapsed)

        try:
            response = await asyncio.to_thread(
                lambda: self.openai_client.completions.create(
                    model="gpt-4",
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.9
                )
            )
            self.last_api_call_time = time.time()
            return response.choices[0].text.strip()
        except Exception as e:
            logger.error(f"Error generating poetry: {e}")
            return "Error generating poetic response"

    async def process_packets(self, style: PoetryStyle = PoetryStyle.PESSOA):
        """
        Real-time packet capturing with asynchronous buffering:
        Once we've accumulated enough packets, generate a poem.
        """

        async def buffer_processor():
            while True:
                if len(self.packet_buffer) >= self.buffer_size:
                    prompt = self.craft_prompt(self.packet_buffer, style)
                    poem = await self.generate_poetry(prompt)

                    archive_entry = PoetryArchiveEntry(
                        poetry=poem,
                        packets=[vars(p) for p in self.packet_buffer],
                        style=style.value
                    )

                    # Use the generation timestamp as our key
                    self.poetry_archive[archive_entry.generated_at] = archive_entry

                    # Clear the buffer for the next cycle
                    self.packet_buffer.clear()

                    logger.info(
                        f"\n--- New Poetry Generated at {archive_entry.generated_at} ---\n{poem}\n"
                    )

                await asyncio.sleep(1)

        # Begin the asynchronous buffer processor
        buffer_task = asyncio.create_task(buffer_processor())

        # Main loop sniffing packets
        try:
            for packet in self.capture.sniff_continuously():
                packet_data = self.extract_packet_data(packet)
                if packet_data:
                    self.packet_buffer.append(packet_data)
                await asyncio.sleep(0.01)
        except KeyboardInterrupt:
            logger.info("Interrupted by user, stopping packet capture.")
            buffer_task.cancel()
        finally:
            self.save_archive()

    def save_archive(self):
        """
        Serializes the entire poetry archive to a JSON file for posterity.
        """
        try:
            archive_dict = {
                timestamp: {
                    'poetry': entry.poetry,
                    'packets': entry.packets,
                    'style': entry.style,
                    'generated_at': entry.generated_at
                }
                for timestamp, entry in self.poetry_archive.items()
            }

            with open('network_poetry_archive.json', 'w') as f:
                json.dump(archive_dict, f, indent=2)

            logger.info("Poetry archive saved successfully.")
        except Exception as e:
            logger.error(f"Error saving poetry archive: {e}")


async def main():
    """
    Entry point for the Digital Heteronyms script. 
    Attempts to fetch the OPENAI_API_KEY from environment variables.
    """
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set. Exiting.")
        return

    # Instantiate DigitalHeteronyms with a chosen network interface.
    # Adjust buffer_size and rate_limit_seconds as needed.
    generator = DigitalHeteronyms(
        interface='eth0',
        openai_api_key=openai_api_key,
        buffer_size=5,
        rate_limit_seconds=1.0
    )
    await generator.process_packets(style=PoetryStyle.PESSOA)


if __name__ == "__main__":
    asyncio.run(main())


# ---------------------------------------------------------------------------
#                           EXPANDED DISCLAIMER
# ---------------------------------------------------------------------------
#
# Legal & Ethical Considerations
# ------------------------------
# 1. Network Monitoring Compliance:
#    - Only capture and analyze traffic on networks you own or where you have
#      written authorization.
#    - Adhere to relevant regulations (GDPR, CCPA, local privacy laws).
#
# 2. Data Privacy & Security:
#    - This script is intended for metadata analysis only—avoid inspecting payloads.
#    - Mask sensitive data (e.g., IP anonymization) to protect user privacy.
#    - Use encrypted storage for logs and maintain strict access controls.
#
# 3. API Usage Compliance (OpenAI):
#    - Abide by OpenAI's Terms of Service and usage policies.
#    - Monitor or limit your calls to avoid rate limit breaches.
#    - Store credentials securely (e.g., environment variables, not hard-coded).
#
# 4. Ethical Guidelines:
#    - Acceptable Use Cases: Artistic, educational, research, authorized network
#      analysis, etc.
#    - Prohibited Activities: Unauthorized surveillance, malicious data harvest,
#      privacy violations, and commercial exploitation without proper licensing.
#
# 5. Limitation of Liability:
#    - Provided "as-is" with no warranties.
#    - The authors are not responsible for misuse or any legal ramifications.
#    - Users must consult legal professionals regarding compliance and liability.
#
# ---------------------------------------------------------------------------
#
#   "The packet not taken makes all the difference" 
#       — Robert Frost, if he were a network engineer
#
# ---------------------------------------------------------------------------
