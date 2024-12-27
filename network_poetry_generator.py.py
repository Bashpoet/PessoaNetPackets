What about this iteration? Which version is the better and why? 

"import os

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



@dataclass

class PoetryArchiveEntry:

    poetry: str

    packets: List[dict]

    style: str

    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())



class NetworkPoetryGenerator:

    def __init__(

        self,

        interface: str,

        openai_api_key: str,

        buffer_size: int = 5,

        rate_limit_seconds: float = 1.0

    ):

        """

        Initialize the network poetry generator with:

          - pyshark LiveCapture instance for packet sniffing.

          - OpenAI setup with the provided API key.

          - Internal buffers for storing packets before generating poems.

        """

        self.interface = interface

        self.buffer_size = buffer_size

        self.rate_limit_seconds = rate_limit_seconds



        # Set up OpenAI

        openai.api_key = openai_api_key



        # Configure the live capture

        self.capture = pyshark.LiveCapture(interface=self.interface)



        # Buffers and archives

        self.packet_buffer: List[PacketData] = []

        self.poetry_archive: Dict[str, PoetryArchiveEntry] = defaultdict()



        self.last_api_call_time = 0.0



    def anonymize_ip(self, ip_address: str) -> str:

        """

        Simple anonymizer: replaces the last two octets with 'x.x' for IPv4 addresses.

        This helps mask specific host details while maintaining a partial sense

        of network structure.

        """

        if ip_address == "Unknown":

            return ip_address

        parts = ip_address.split('.')

        if len(parts) == 4:

            return f"{parts[0]}.{parts[1]}.x.x"

        return ip_address



    def extract_packet_data(self, packet) -> Optional[PacketData]:

        """

        Extract relevant details from the pyshark packet object.

        Return None if extraction fails.

        """

        try:

            ip_layer = getattr(packet, 'ip', None)

            if not ip_layer:

                return None



            src_ip = getattr(ip_layer, 'src', "Unknown")

            dest_ip = getattr(ip_layer, 'dst', "Unknown")

            protocol = getattr(packet, 'transport_layer', "Unknown")

            length = int(packet.length)

            timestamp = time.time()



            port_src, port_dst, flags = None, None, None

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

        Build the prompt sent to OpenAI for poem generation based on the chosen style.

        """

        style_context = {

            PoetryStyle.PESSOA: (

                "Channel the introspective, philosophical voice of Fernando Pessoa's heteronyms. "

                "Contemplate each packet as a fleeting moment of consciousness traversing the ether."

            ),

            PoetryStyle.WHITMAN: (

                "Embrace Walt Whitman's grand, expansive style. "

                "Treat each packet as part of a cosmic tapestry of modern life."

            ),

            PoetryStyle.DICKINSON: (

                "Employ Emily Dickinson's delicate yet potent verse. "

                "Observe the micro-moments of transmission with a keen, reverent eye."

            )

        }



        packet_descriptions = []

        for packet in packets:

            line = (

                f"Data from {packet.src_ip}:{packet.port_src} "

                f"to {packet.dest_ip}:{packet.port_dst}, "

                f"{packet.length} bytes via {packet.protocol}."

            )

            packet_descriptions.append(line)



        joined_descriptions = "\n".join(packet_descriptions)



        return f"""

{style_context[style]}



We have the following network occurrences:

{joined_descriptions}



Transform these ephemeral flows into a poem in the style of {style.value}.

Reflect on intangible data in our digital consciousness, and any deeper metaphorical texture.

        """



    async def generate_poetry(self, prompt: str) -> str:

        """

        Query the OpenAI API to generate poetry. Enforces a simple time-based rate limit.

        """

        elapsed = time.time() - self.last_api_call_time

        if elapsed < self.rate_limit_seconds:

            await asyncio.sleep(self.rate_limit_seconds - elapsed)



        try:

            # Using the modern ChatCompletion endpoint

            response = await asyncio.to_thread(

                lambda: openai.ChatCompletion.create(

                    model="gpt-4",

                    messages=[{"role": "user", "content": prompt}],

                    max_tokens=250,

                    temperature=0.9

                )

            )

            self.last_api_call_time = time.time()

            return response.choices[0].message.content.strip()

        except Exception as e:

            logger.error(f"Error generating poetry from OpenAI: {e}")

            return "Error generating poetic response"



    async def process_packets(self, style: PoetryStyle = PoetryStyle.PESSOA):

        """

        Asynchronously sniff packets in real time, assemble them into poems once buffer_size is reached.

        """

        async def buffer_processor():

            while True:

                if len(self.packet_buffer) >= self.buffer_size:

                    # Turn the batch of packets into a poem

                    prompt = self.craft_prompt(self.packet_buffer, style)

                    poetry = await self.generate_poetry(prompt)



                    entry = PoetryArchiveEntry(

                        poetry=poetry,

                        packets=[vars(p) for p in self.packet_buffer],

                        style=style.value

                    )

                    self.poetry_archive[entry.generated_at] = entry



                    # Clear the buffer

                    self.packet_buffer.clear()



                    logger.info(

                        f"\n--- New Poetry Generated at {entry.generated_at} ---\n{poetry}\n"

                    )

                await asyncio.sleep(1)



        # Kick off our buffer_processor task in the event loop

        processor_task = asyncio.create_task(buffer_processor())



        try:

            # We'll iterate with sniff_continuously, but add an await to yield control between captures

            for packet in self.capture.sniff_continuously():

                packet_data = self.extract_packet_data(packet)

                if packet_data:

                    self.packet_buffer.append(packet_data)

                await asyncio.sleep(0.01)

        except KeyboardInterrupt:

            logger.info("Stopping packet capture due to user interruption...")

        finally:

            processor_task.cancel()

            self.save_archive()



    def save_archive(self):

        """

        Store the entire poetry archive to a JSON file. Keeps anonymized data from PacketData.

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

    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if not openai_api_key:

        logger.error("Error: OPENAI_API_KEY environment variable not set.")

        return



    # Example usage

    generator = NetworkPoetryGenerator(

        interface='eth0',

        openai_api_key=openai_api_key,

        buffer_size=5,

        rate_limit_seconds=1.0

    )

    await generator.process_packets(style=PoetryStyle.PESSOA)



if __name__ == "__main__":

    asyncio.run(main())

