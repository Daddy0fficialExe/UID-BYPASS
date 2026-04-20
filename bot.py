import os
import json
import time
import asyncio
import discord
from discord import app_commands

CLEAN_INTERVAL = 60
PERMANENT_EXPIRY = 9999999999  # Year 2286, effectively permanent

# List of allowed channel IDs where commands will work
ALLOWED_CHANNELS = [
    1423737925803311165,  # Replace with your channel ID 1
    1423737925803311165,  # Replace with your channel ID 2
    # Add more channel IDs as needed
]


def load_whitelist(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Convert to {uid: {"name": name, "expiry": expiry}} format
            whitelist_data = {}
            for uid, value in data.items():
                if isinstance(value, dict):
                    whitelist_data[uid] = value
                else:
                    whitelist_data[uid] = {"name": "Unknown", "expiry": int(value)}
            return whitelist_data
    except:
        return {}


def save_whitelist(wl, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(wl, f, separators=(",", ":"), ensure_ascii=False)
    os.replace(tmp, path)


async def _send_channel_error(interaction: discord.Interaction):
    try:
        await interaction.response.send_message(
            f"❌ This command can only be used in specific channels!\n"
            f"**Allowed Channels:** {', '.join(f'<#{cid}>' for cid in ALLOWED_CHANNELS)}",
            ephemeral=True
        )
    except Exception as e:
        print(f"Failed to send channel error message: {e}")


def channel_check(interaction: discord.Interaction) -> bool:
    """Check if the command is used in an allowed channel"""
    if interaction.channel_id in ALLOWED_CHANNELS:
        return True
    
    # If not in allowed channel, send error message
    asyncio.create_task(_send_channel_error(interaction))
    return False


class WhitelistCog(app_commands.Group):
    def __init__(self, bot_name, file_path):
        super().__init__(name="whitelist", description="Manage whitelist")
        self.path = file_path
        self.wl = load_whitelist(self.path)
        self.bot_name = bot_name

    async def sexy_embed(self, title, desc, color=0x9B59B6):
        e = discord.Embed(title=f"✨ {title} ✨", description=desc, color=color)
        e.set_footer(text=f"{self.bot_name} • Whitelist Manager ⚡", icon_url="https://cdn.discordapp.com/emojis/903069137422565406.gif")
        e.set_thumbnail(url="https://cdn.discordapp.com/attachments/903069137422565406/1182390234879942746/neon_icon.gif")
        e.timestamp = discord.utils.utcnow()
        return e

    @app_commands.command(name="add", description="Add user to whitelist with name")
    @app_commands.describe(
        uid="User ID to whitelist",
        name="Display name for the user",
        hours="Number of hours (default: 24)",
        days="Number of days (default: 0)",
        months="Number of months (default: 0)",
        permanent="Set to True for permanent whitelist"
    )
    async def add(self, interaction: discord.Interaction, uid: str, name: str, 
                 hours: int = 24, days: int = 0, months: int = 0, permanent: bool = False):
        """Add user to whitelist with flexible duration options"""
        
        # Channel check
        if not channel_check(interaction):
            return
        
        if permanent:
            expire = PERMANENT_EXPIRY
            duration_text = "♾️ **Permanent** (Never expires)"
        else:
            # Calculate total seconds
            total_seconds = 0
            total_seconds += months * 30 * 24 * 3600  # Approximate 30 days per month
            total_seconds += days * 24 * 3600
            total_seconds += hours * 3600
            
            if total_seconds <= 0:
                await interaction.response.send_message(
                    "❌ Please specify at least some duration (hours, days, or months) or set permanent=True!",
                    ephemeral=True
                )
                return
            
            expire = int(time.time()) + total_seconds
            
            # Create readable duration text
            duration_parts = []
            if months > 0:
                duration_parts.append(f"{months} month(s)")
            if days > 0:
                duration_parts.append(f"{days} day(s)")
            if hours > 0:
                duration_parts.append(f"{hours} hour(s)")
            
            duration_text = "⏳ **Duration:** " + ", ".join(duration_parts) + f" (<t:{expire}:R>)"
        
        self.wl[str(uid)] = {"name": name, "expiry": expire}
        save_whitelist(self.wl, self.path)

        msg = f"🆔 **User ID:** `{uid}`\n📛 **Name:** {name}\n{duration_text}"
        await interaction.response.send_message(embed=await self.sexy_embed("✅ Added to Whitelist", msg, 0x2ECC71))

    @app_commands.command(name="remove", description="Remove a user from whitelist")
    @app_commands.describe(uid="User ID to remove from whitelist")
    async def remove(self, interaction: discord.Interaction, uid: str):
        """Remove a user from whitelist"""
        
        # Channel check
        if not channel_check(interaction):
            return
        
        if str(uid) not in self.wl:
            await interaction.response.send_message(embed=await self.sexy_embed("❔ Not Found", f"`{uid}` is not in whitelist.", 0xF1C40F))
            return

        name = self.wl[str(uid)].get("name", "Unknown")
        expiry = self.wl[str(uid)].get("expiry", 0)
        
        # Check if it was permanent
        if expiry >= PERMANENT_EXPIRY - 1000000:  # Close enough to permanent
            duration_info = "♾️ (Permanent)"
        else:
            duration_info = f"Expired: <t:{expiry}:R>"
        
        del self.wl[str(uid)]
        save_whitelist(self.wl, self.path)
        
        msg = f"🗑️ `{uid}` ({name}) removed from whitelist.\n{duration_info}"
        await interaction.response.send_message(embed=await self.sexy_embed("🗑️ Removed", msg, 0xE67E22))

    @app_commands.command(name="list", description="Show all whitelisted users")
    async def list(self, interaction: discord.Interaction):
        """Show all whitelisted users"""
        
        # Channel check
        if not channel_check(interaction):
            return
        
        if not self.wl:
            await interaction.response.send_message(embed=await self.sexy_embed("📜 Whitelist Empty", "Nobody is currently whitelisted.", 0x95A5A6))
            return

        lines = []
        for uid, data in sorted(self.wl.items(), key=lambda x: x[1].get("expiry", 0)):
            name = data.get("name", "Unknown")
            expiry = data.get("expiry", 0)
            
            if expiry >= PERMANENT_EXPIRY - 1000000:  # Permanent
                expiry_text = "♾️ **Permanent**"
            else:
                expiry_text = f"Expires: <t:{expiry}:R>"
            
            lines.append(f"💠 `{uid}` - **{name}**\n   {expiry_text}")
        
        desc = "\n\n".join(lines)
        await interaction.response.send_message(embed=await self.sexy_embed("👑 Whitelisted Users", desc, 0x1ABC9C))

    @app_commands.command(name="check", description="Check if a user is whitelisted")
    @app_commands.describe(uid="User ID to check")
    async def check(self, interaction: discord.Interaction, uid: str):
        """Check if a user is whitelisted"""
        
        # Channel check
        if not channel_check(interaction):
            return
        
        data = self.wl.get(str(uid))
        if not data:
            await interaction.response.send_message(embed=await self.sexy_embed("❌ Not Whitelisted", f"`{uid}` is **not** in whitelist.", 0xE74C3C))
            return
        
        expiry = data.get("expiry", 0)
        name = data.get("name", "Unknown")
        
        if expiry <= int(time.time()):
            del self.wl[str(uid)]
            save_whitelist(self.wl, self.path)
            msg = f"`{uid}` ({name}) was expired and removed."
            await interaction.response.send_message(embed=await self.sexy_embed("⌛ Expired", msg, 0xE67E22))
            return
        
        if expiry >= PERMANENT_EXPIRY - 1000000:  # Permanent
            status = "♾️ **Permanent** (Never expires)"
        else:
            status = f"⏳ Expires: <t:{expiry}:F> (<t:{expiry}:R>)"
        
        msg = f"✅ **`{uid}`** ({name})\n{status}"
        await interaction.response.send_message(embed=await self.sexy_embed("✅ Active", msg, 0x2ECC71))

    @app_commands.command(name="permanent", description="Add permanent user to whitelist")
    @app_commands.describe(
        uid="User ID to whitelist permanently",
        name="Display name for the user"
    )
    async def permanent(self, interaction: discord.Interaction, uid: str, name: str):
        """Add a permanent UID to whitelist"""
        
        # Channel check
        if not channel_check(interaction):
            return
        
        expire = PERMANENT_EXPIRY
        self.wl[str(uid)] = {"name": name, "expiry": expire}
        save_whitelist(self.wl, self.path)

        msg = f"🆔 **User ID:** `{uid}`\n📛 **Name:** {name}\n♾️ **Status:** Permanent (Never expires)"
        await interaction.response.send_message(embed=await self.sexy_embed("✅ Added Permanent User", msg, 0x2ECC71))

    @app_commands.command(name="update_name", description="Update name for existing UID")
    @app_commands.describe(
        uid="User ID to update",
        new_name="New display name"
    )
    async def update_name(self, interaction: discord.Interaction, uid: str, new_name: str):
        """Update the display name for an existing UID"""
        
        # Channel check
        if not channel_check(interaction):
            return
        
        if str(uid) not in self.wl:
            await interaction.response.send_message(embed=await self.sexy_embed("❔ Not Found", f"`{uid}` is not in whitelist.", 0xF1C40F))
            return
        
        old_name = self.wl[str(uid)].get("name", "Unknown")
        self.wl[str(uid)]["name"] = new_name
        save_whitelist(self.wl, self.path)
        
        msg = f"📝 **`{uid}`**\nOld name: {old_name}\nNew name: {new_name}"
        await interaction.response.send_message(embed=await self.sexy_embed("✅ Name Updated", msg, 0x3498DB))

    @app_commands.command(name="channels", description="Show allowed channels for commands")
    async def channels(self, interaction: discord.Interaction):
        """Show which channels are allowed for commands"""
        
        # This command works everywhere to help users know where to go
        if ALLOWED_CHANNELS:
            channel_mentions = [f"<#{cid}>" for cid in ALLOWED_CHANNELS]
            desc = f"**Commands can only be used in:**\n" + "\n".join(channel_mentions)
        else:
            desc = "❌ No channels configured. Please contact the bot administrator."
        
        await interaction.response.send_message(embed=await self.sexy_embed("📌 Allowed Channels", desc, 0x7289DA))


async def cleaner_task(group):
    while True:
        now = int(time.time())
        expired = [uid for uid, data in list(group.wl.items()) 
                  if data.get("expiry", 0) <= now and data.get("expiry", 0) < PERMANENT_EXPIRY - 1000000]
        for uid in expired:
            del group.wl[uid]
        if expired:
            save_whitelist(group.wl, group.path)
            print(f"Cleaned {len(expired)} expired entries")
        await asyncio.sleep(CLEAN_INTERVAL)


async def start_bot(token, name, file_path):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    wl = WhitelistCog(name, file_path)

    @client.event
    async def on_ready():
        tree.add_command(wl)
        await tree.sync()
        client.loop.create_task(cleaner_task(wl))
        print(f"💎 {name} logged in as {client.user} ({client.user.id})")

    await client.start(token)


async def main(): 
    token2 = "MTQ2MTM2ODIwMTQ1ODg4MDU2Ng.GrA9Pd.d7Ew_I4jWyJplPbyj3VufMGB1iz9Caj5vxneQs"

    # IMPORTANT: Replace these with your actual channel IDs
    # To get channel ID: Right-click channel → Copy ID (enable Developer Mode in Discord settings)
    ALLOWED_CHANNELS.clear()
    ALLOWED_CHANNELS.extend([
        1461367589732090030,  # Example channel ID 1
        1461367589732090030,  # Example channel ID 2
        # Add your channel IDs here
    ])

    await asyncio.gather(     
        start_bot(token2, "💎 DADDY OFFICIAL", "whitelist_ind.json"),
    )

asyncio.run(main())