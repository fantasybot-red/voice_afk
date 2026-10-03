import os
import asyncio
import random
from typing import Tuple, Sequence

import aiohttp
from dotenv import load_dotenv

if os.getenv("IS_DOCKER") is None:
    load_dotenv()

import discord
from discord import utils, StreamKey

DETECTABLE_ACTIVITIES = None

class Client(discord.Client):
    def __init__(self, channel_id):
        self.channel_id = channel_id
        self.channel = None
        super().__init__()

    async def connect_voice(self):
        deaf = (os.getenv("IS_DEAF", "false").lower() == "true")
        mute = (os.getenv("IS_MUTE", "true").lower() == "true")
        stream = (os.getenv("IS_STREAM", "false").lower() == "true")
        video = (os.getenv("IS_VIDEO", "false").lower() == "true")
        await self.channel.guild.change_voice_state(
            channel=self.channel, self_deaf=deaf, self_mute=mute, self_video=video
        )
        skey = StreamKey.from_guild(guild_id=self.channel.guild.id, channel_id=self.channel.id, owner_id=self.user.id)
        if stream:
            await asyncio.sleep(2)
            await self._connection.ws.stream_create(
                stream_type=skey.type.value,
                guild_id=self.channel.guild.id,
                channel_id=self.channel.id,
            )
            image_url = os.getenv("STREAM_IMAGE_URL")
            if image_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            await self._connection.http.upload_stream_preview(
                                str(skey), utils._bytes_to_base64_data(image_data)
                            )
                        else:
                            print(f"[{self.user.name}] Failed to fetch image from {image_url}. Status code: {response.status}")

    async def on_ready(self):
        print(f'[{self.user.name}] Logged in as {self.user.name} ({self.user.id})')
        print('------')
        self.channel = self.get_channel(self.channel_id)
        if self.channel is None:
            print(f'[{self.user.name}] Channel with ID {self.channel_id} not found.')
            return
        await self.connect_voice()

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member != self.user:
            return  # Ignore updates for the bot itself

        if self.channel is None:
            print(f'[{self.user.name}] Channel with ID {self.channel_id} not found.')
            return
        
        if member.guild.id != self.channel.guild.id:
            return # Pervent update when join on other servers
        
        if after.channel is None:
            await asyncio.sleep(1)
            new_member = member.guild.get_member(self.user.id)
            if new_member is not None and new_member.voice is not None and new_member.voice.channel is not None:
                print(f"[{self.user.name}] Reconnected to voice channel.")
                return
            print(f"[{self.user.name}] Disconnected from voice channel. Attempting to reconnect...")
            await self.connect_voice()

async def main():
    utils.setup_logging()
    tasks = []
    tokens = os.environ
    for token in tokens:
        if token.startswith("DISCORD_TOKEN_"):
            channel_id = int(token.split("_")[-1]) # Get the channel ID from the token name
            client = Client(channel_id)
            tasks.append(client.start(tokens[token]))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
