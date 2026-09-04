import os
import asyncio
from dotenv import load_dotenv

if os.getenv("IS_DOCKER") is None:
    load_dotenv()

import discord
from discord import utils

class Client(discord.Client):
    def __init__(self, channel_id):
        self.channel_id = channel_id
        super().__init__()

    async def connect_voice(self):
        channel = self.get_channel(self.channel_id)
        if channel is None:
            print(f'[{self.user.name}] Channel with ID {self.channel_id} not found.')
            return
        await channel.connect(self_mute=True, reconnect=False)

    async def on_ready(self):
        print(f'[{self.user.name}] Logged in as {self.user.name} ({self.user.id})')
        print('------')
        await self.connect_voice()

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member != self.user:
            return  # Ignore updates for the bot itself

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