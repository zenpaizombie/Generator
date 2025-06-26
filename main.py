import discord
from discord.ext import commands
import subprocess
import asyncio

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Constants
SERVER_LIMIT = 10 
AUTHORIZED_ROLE_IDS = []  # Replace with role IDs who can use deploy commands
database_file = "servers.txt"
TOKEN = ""  # Place your bot's token here
SERVER = "VPS-I9"  # Your server name for bot presence

# Helper Functions
def count_user_servers(user_id):
    try:
        with open(database_file, 'r') as f:
            return sum(1 for line in f if line.startswith(user_id))
    except FileNotFoundError:
        return 0

def add_to_database(user, container_id, ssh_command):
    with open(database_file, 'a') as f:
        f.write(f"{user}|{container_id}|{ssh_command}\n")

def list_servers():
    try:
        with open(database_file, 'r') as f:
            return f.readlines()
    except FileNotFoundError:
        return ["No servers found."]

async def capture_ssh_command(process):
    max_retries = 60  # up to 60 seconds
    ssh_command = None
    for _ in range(max_retries):
        line = await process.stdout.readline()
        if line:
            decoded_line = line.decode().strip()
            print(f"tmate output: {decoded_line}")
            if "ssh " in decoded_line and "ro-" not in decoded_line:
                ssh_command = decoded_line
                break
        await asyncio.sleep(1)
    return ssh_command

async def deploy_server(ctx, target_user, ram, cores):
    user_id = str(target_user.id)

    if count_user_servers(user_id) >= SERVER_LIMIT:
        await ctx.send(embed=discord.Embed(
            description="```Error: Instance Limit Reached```", color=0xff0000))
        return

    image = "ubuntu-22.04-with-tmate"
    try:
        container_id = subprocess.check_output([
            "docker", "run", "-d", "--privileged", "--cap-add=ALL",
            "--memory", ram, "--cpus", str(cores), image
        ]).strip().decode('utf-8')

        await asyncio.sleep(5)  # Give container time to initialize

        exec_cmd = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id, "tmate", "-F",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        ssh_session_line = await capture_ssh_command(exec_cmd)

        if ssh_session_line:
            await target_user.send(embed=discord.Embed(
                description=f"### ✅ Instance Created\n"
                            f"**SSH Command:** ```{ssh_session_line}```\nOS: Ubuntu 22.04",
                color=0x00ff00))
            add_to_database(user_id, container_id, ssh_session_line)
            await ctx.send(embed=discord.Embed(
                description=f"Instance created. SSH details sent to {target_user.mention}.", 
                color=0x00ff00))
        else:
            await ctx.send(embed=discord.Embed(
                description="Instance creation failed or timed out. Please try again later.",
                color=0xff0000))
            subprocess.run(["docker", "rm", "-f", container_id])
    except subprocess.CalledProcessError as e:
        await ctx.send(embed=discord.Embed(
            description=f"Error creating container: {e}", color=0xff0000))

@bot.command(name="deploy")
async def deploy(ctx, userid: int, ram: str, cores: int):
    if any(role.id in AUTHORIZED_ROLE_IDS for role in ctx.author.roles):
        try:
            target_user = await bot.fetch_user(userid)
            if target_user:
                await ctx.send(embed=discord.Embed(
                    description="⏳ Creating Instance. Please wait...", color=0x00ff00))
                await deploy_server(ctx, target_user, ram, cores)
        except discord.NotFound:
            await ctx.send(embed=discord.Embed(
                description=f"User with ID {userid} not found.", color=0xff0000))
    else:
        await ctx.send(embed=discord.Embed(
            description="🚫 You don't have permission to deploy instances.", color=0xff0000))

@bot.command(name="ressh")
async def ressh(ctx, container_id: str, userid: int):
    try:
        subprocess.run(["docker", "start", container_id], stdout=subprocess.DEVNULL)
        await asyncio.sleep(3)
        exec_cmd = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id, "tmate", "-F",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        ssh_session_line = await capture_ssh_command(exec_cmd)

        if ssh_session_line:
            target_user = await bot.fetch_user(userid)
            await target_user.send(embed=discord.Embed(
                description=f"🔁 New SSH Session: ```{ssh_session_line}```",
                color=0x00ff00))
            await ctx.send(embed=discord.Embed(
                description=f"SSH info resent to {target_user.mention}.", color=0x00ff00))
        else:
            await ctx.send(embed=discord.Embed(
                description="⚠️ Failed to get SSH session.", color=0xff0000))
    except Exception as e:
        await ctx.send(embed=discord.Embed(
            description=f"Error: {e}", color=0xff0000))

@bot.command(name="list")
async def list_all_servers(ctx):
    if not any(role.id in AUTHORIZED_ROLE_IDS for role in ctx.author.roles):
        await ctx.send(embed=discord.Embed(
            description="🚫 You don't have permission to use this command.",
            color=0xff0000))
        return

    try:
        with open(database_file, 'r') as f:
            server_details = f.readlines()
    except FileNotFoundError:
        await ctx.send(embed=discord.Embed(
            description="No server data found.",
            color=0xff0000))
        return

    if server_details:
        msg = "**📄 Active Servers:**\n\n"
        msg += "```User ID       | Container ID        | SSH Command\n"
        msg += "-"*65 + "\n"
        for line in server_details:
            user_id, cid, ssh = line.strip().split("|")
            msg += f"{user_id[:10]:<13}| {cid[:20]:<20}| {ssh[:25]}...\n"
        msg += "```"
    else:
        msg = "No active servers."

    try:
        await ctx.author.send(msg)
        await ctx.send(embed=discord.Embed(
            description="✅ Server list sent via DM.", color=0x00ff00))
    except discord.Forbidden:
        await ctx.send(embed=discord.Embed(
            description="❌ I couldn't DM you. Please enable DMs.", color=0xff0000))

@bot.command(name="delete")
async def delete_container(ctx, container_id: str):
    try:
        subprocess.run(["docker", "rm", "-f", container_id])
        await ctx.send(embed=discord.Embed(
            description=f"🗑️ Container `{container_id}` deleted.", color=0x00ff00))
    except subprocess.CalledProcessError as e:
        await ctx.send(embed=discord.Embed(
            description=f"⚠️ Error deleting container: {e}", color=0xff0000))

@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game(name=SERVER)
    )
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)
