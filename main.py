import os
import asyncio
import random
from typing import Tuple, Sequence

import aiohttp
from discord.ext import tasks
from dotenv import load_dotenv

if os.getenv("IS_DOCKER") is None:
    load_dotenv()

import discord
from discord import utils, Stream, StreamDeleteReason, StreamKey, VoiceStream, VoiceCodec

DETECTABLE_ACTIVITIES = None

class StreamClient(discord.StreamProtocol):
    voice_client: discord.VoiceClient

    def supports_video(self) -> bool:
        return True

    def get_experiments(self, ready_experiments: Sequence[str]) -> Sequence[str]:
        return ()

    @property
    def codecs(self) -> Tuple[VoiceCodec, ...]:
        return (VoiceCodec.opus(),)

    @property
    def video_streams(self) -> Tuple[VoiceStream, ...]:
        return (VoiceStream.video(),)

    @property
    def stream_key(self) -> StreamKey:
        return self.stream.key


    async def on_stream_server_update(self, data: dict, /) -> None:
        pass


    async def on_stream_delete(self, stream: Stream, reason: StreamDeleteReason, /) -> None:
        if self.voice_client.is_connected() and reason not in [
            StreamDeleteReason.unauthorized,
            StreamDeleteReason.invalid_channel
        ]:
            await self.voice_client.create_stream(cls=StreamClient)


    async def connect(self, *, timeout: float, reconnect: bool) -> None:
        pass

    async def disconnect(self, *, force: bool) -> None:
        self.cleanup()


class Client(discord.Client):
    def __init__(self, channel_id):
        self.channel_id = channel_id
        self.channel = None
        super().__init__()

    @tasks.loop(minutes=25)
    async def game_status(self):
        random_activity = random.choice(DETECTABLE_ACTIVITIES)
        await self.change_presence(activity=
            discord.Activity(
                type=discord.ActivityType.playing,
                name=random_activity["name"],
                application_id=random_activity["id"],
                parent_application_id=random_activity["id"],
                platform=discord.ActivityPlatform.desktop,
            )
        )

    async def connect_voice(self):
        deaf = (os.getenv("IS_DEAF", "false").lower() == "true")
        mute = (os.getenv("IS_MUTE", "true").lower() == "true")
        stream = (os.getenv("IS_STREAM", "false").lower() == "true")
        vc = await self.channel.connect(self_deaf=deaf, self_mute=mute, reconnect=False)
        if stream:
            await vc.create_stream(cls=StreamClient)

    async def on_ready(self):
        print(f'[{self.user.name}] Logged in as {self.user.name} ({self.user.id})')
        print('------')
        self.channel = self.get_channel(self.channel_id)
        if self.channel is None:
            print(f'[{self.user.name}] Channel with ID {self.channel_id} not found.')
            return
        await self.connect_voice()
        await self.game_status()
        if not self.game_status.is_running():
            self.game_status.start()

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
            if before.channel.guild.voice_client is not None:
                await before.channel.guild.voice_client.disconnect(force=True)
            print(f"[{self.user.name}] Disconnected from voice channel. Attempting to reconnect...")
            await self.connect_voice()


async def fetch_discoverable_activities():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://discord.com/api/v10/games/detectable") as response:
            return await response.json()

async def main():
    global DETECTABLE_ACTIVITIES
    DETECTABLE_ACTIVITIES = await fetch_discoverable_activities()
    print(f"Fetched {len(DETECTABLE_ACTIVITIES)} detectable activities.")
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
