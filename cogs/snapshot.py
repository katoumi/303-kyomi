import asyncio
import io
import json
import discord
from discord import app_commands
from discord.ext import commands
from ui_theme import (
    COLOR_AMBER,
    COLOR_CRIMSON,
    COLOR_MINT,
    COLOR_OBSIDIAN,
    kyomi_embed,
)


def serialize_guild_structure(guild: discord.Guild) -> tuple[dict, dict, dict]:
    """Serializes all roles, categories, channels, and permission overwrites."""
    # 1. Roles
    roles_data = []
    for role in guild.roles:
        if role == guild.default_role:
            continue
        roles_data.append({
            "id": role.id,
            "name": role.name,
            "color": role.color.value,
            "hoist": role.hoist,
            "position": role.position,
            "permissions": role.permissions.value,
            "mentionable": role.mentionable,
            "managed": role.managed,
        })

    # 2. Channels & Categories
    channels_data = []
    for ch in guild.channels:
        # Determine channel type string
        if isinstance(ch, discord.CategoryChannel):
            ch_type = "category"
        elif isinstance(ch, discord.TextChannel):
            ch_type = "news" if ch.is_news() else "text"
        elif isinstance(ch, discord.VoiceChannel):
            ch_type = "voice"
        elif isinstance(ch, discord.StageChannel):
            ch_type = "stage"
        elif isinstance(ch, discord.ForumChannel):
            ch_type = "forum"
        else:
            ch_type = "other"

        # Overwrites
        overwrites_data = []
        for target, overwrite in ch.overwrites.items():
            allow_val, deny_val = overwrite.pair()
            overwrites_data.append({
                "target_type": "role" if isinstance(target, discord.Role) else "member",
                "target_id": target.id,
                "target_name": target.name,
                "allow": allow_val.value,
                "deny": deny_val.value,
            })

        channels_data.append({
            "id": ch.id,
            "name": ch.name,
            "type": ch_type,
            "position": ch.position,
            "category_id": ch.category_id,
            "category_name": ch.category.name if ch.category else None,
            "topic": getattr(ch, "topic", None),
            "slowmode_delay": getattr(ch, "slowmode_delay", 0),
            "nsfw": getattr(ch, "nsfw", False),
            "bitrate": getattr(ch, "bitrate", None),
            "user_limit": getattr(ch, "user_limit", None),
            "overwrites": overwrites_data,
        })

    # 3. Metadata
    metadata = {
        "guild_id": guild.id,
        "guild_name": guild.name,
        "member_count": guild.member_count,
        "roles_count": len(roles_data),
        "channels_count": len(channels_data),
        "categories_count": len([c for c in channels_data if c["type"] == "category"]),
    }

    return roles_data, channels_data, metadata


class ConfirmRestoreView(discord.ui.View):
    def __init__(self, cog: "SnapshotCog", snapshot_data: dict, author: discord.Member):
        super().__init__(timeout=60)
        self.cog = cog
        self.snapshot_data = snapshot_data
        self.author = author

    @discord.ui.button(
        label="✦ confirm restore",
        style=discord.ButtonStyle.danger,
        custom_id="snapshot:confirm_restore",
    )
    async def confirm_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                "*only the administrator who initiated this can confirm.*", ephemeral=True
            )

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)

        await self.cog.execute_restore(interaction, self.snapshot_data)

    @discord.ui.button(
        label="× cancel",
        style=discord.ButtonStyle.secondary,
        custom_id="snapshot:cancel_restore",
    )
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                "*only the administrator who initiated this can cancel.*", ephemeral=True
            )

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(
            content="╰ *restore cancelled.*", embed=None, view=self
        )


class SnapshotCog(commands.Cog, name="Snapshot"):
    """Server Structure Snapshot, disaster recovery & emergency channel restore."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    snapshot_group = app_commands.Group(
        name="snapshot",
        description="server structure backup, drift diff, and disaster recovery.",
        default_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )

    @snapshot_group.command(
        name="create",
        description="take a snapshot of all channels, categories, roles, and permissions.",
    )
    async def snapshot_create(
        self,
        interaction: discord.Interaction,
        label: str = "manual backup",
    ):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        roles_data, channels_data, meta = serialize_guild_structure(interaction.guild)
        snapshot_id = await self.bot.db.save_snapshot(
            interaction.guild.id,
            interaction.user.id,
            label,
            json.dumps(roles_data),
            json.dumps(channels_data),
            json.dumps(meta),
        )

        embed = kyomi_embed(
            title=f"snapshot #{snapshot_id:03d}  ·  `{label.lower()}`",
            description=(
                f"╰ **roles captured:** `{meta['roles_count']}`\n"
                f"╰ **categories:** `{meta['categories_count']}`\n"
                f"╰ **channels:** `{meta['channels_count'] - meta['categories_count']}`\n"
                f"╰ **permissions:** all overwrites preserved\n\n"
                f"*saved to persistent SQLite storage. use `/snapshot restore {snapshot_id}` if recovery is ever needed.*"
            ),
            color=COLOR_MINT,
            tag="303  •  snapshot",
            guild=interaction.guild,
        )
        embed.timestamp = None
        await interaction.followup.send(embed=embed, ephemeral=True)

    @snapshot_group.command(
        name="list",
        description="list all saved server snapshots.",
    )
    async def snapshot_list(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        snapshots = await self.bot.db.get_snapshots(interaction.guild.id)
        if not snapshots:
            return await interaction.response.send_message(
                "*no snapshots found. create one with `/snapshot create`.*",
                ephemeral=True,
            )

        lines = ["**saved server snapshots**"]
        for s in snapshots:
            meta = json.loads(s.get("metadata_json") or "{}")
            ch_count = meta.get("channels_count", "?")
            role_count = meta.get("roles_count", "?")
            lines.append(
                f"╰ `#{s['id']:03d}` **{s['label'].lower()}**  ·  `{ch_count}` ch  ·  `{role_count}` roles  ·  <t:{int(discord.utils.snowflake_time(s['id'] if s['id'] > 1000000 else interaction.id).timestamp())}:R>"
            )

        embed = kyomi_embed(
            description="\n".join(lines),
            color=COLOR_OBSIDIAN,
            tag="303  •  backups",
            guild=interaction.guild,
        )
        embed.timestamp = None
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @snapshot_group.command(
        name="diff",
        description="compare current live server structure against a snapshot to detect deleted items.",
    )
    async def snapshot_diff(
        self,
        interaction: discord.Interaction,
        snapshot_id: int | None = None,
    ):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        if snapshot_id is not None:
            snapshot = await self.bot.db.get_snapshot_by_id(snapshot_id)
        else:
            all_snaps = await self.bot.db.get_snapshots(interaction.guild.id)
            snapshot = await self.bot.db.get_snapshot_by_id(all_snaps[0]["id"]) if all_snaps else None

        if not snapshot:
            return await interaction.followup.send(
                "*snapshot not found.*", ephemeral=True
            )

        snap_roles = json.loads(snapshot["roles_json"])
        snap_channels = json.loads(snapshot["channels_json"])

        live_role_names = {r.name.lower() for r in interaction.guild.roles}
        live_channel_names = {c.name.lower() for c in interaction.guild.channels}

        missing_roles = [r["name"] for r in snap_roles if r["name"].lower() not in live_role_names and not r.get("managed")]
        missing_channels = [c["name"] for c in snap_channels if c["name"].lower() not in live_channel_names]

        diff_lines = [f"**structure drift comparison  ·  snapshot `#{snapshot['id']:03d}`**\n"]
        if missing_roles:
            diff_lines.append(f"╰ **missing roles ({len(missing_roles)}):** " + ", ".join(f"`{r}`" for r in missing_roles[:6]))
        else:
            diff_lines.append("╰ **roles:** `all intact`")

        if missing_channels:
            diff_lines.append(f"╰ **missing channels ({len(missing_channels)}):** " + ", ".join(f"`#{c}`" for c in missing_channels[:8]))
        else:
            diff_lines.append("╰ **channels:** `all intact`")

        status_color = COLOR_CRIMSON if (missing_roles or missing_channels) else COLOR_MINT
        embed = kyomi_embed(
            description="\n".join(diff_lines),
            color=status_color,
            tag="303  •  audit",
            guild=interaction.guild,
        )
        embed.timestamp = None
        await interaction.followup.send(embed=embed, ephemeral=True)

    @snapshot_group.command(
        name="export",
        description="download full snapshot JSON file for offline cold storage.",
    )
    async def snapshot_export(
        self,
        interaction: discord.Interaction,
        snapshot_id: int,
    ):
        assert interaction.guild is not None
        snapshot = await self.bot.db.get_snapshot_by_id(snapshot_id)
        if not snapshot:
            return await interaction.response.send_message(
                f"*snapshot `#{snapshot_id}` not found.*", ephemeral=True
            )

        export_data = {
            "snapshot_id": snapshot["id"],
            "guild_id": snapshot["guild_id"],
            "label": snapshot["label"],
            "created_at": snapshot["created_at"],
            "metadata": json.loads(snapshot["metadata_json"]),
            "roles": json.loads(snapshot["roles_json"]),
            "channels": json.loads(snapshot["channels_json"]),
        }
        json_bytes = json.dumps(export_data, indent=2).encode("utf-8")
        file_obj = discord.File(
            io.BytesIO(json_bytes), filename=f"303-snapshot-{snapshot_id:03d}.json"
        )
        await interaction.response.send_message(
            content=f"╰ *exported snapshot `#{snapshot_id:03d}` (`{snapshot['label']}`).*",
            file=file_obj,
            ephemeral=True,
        )

    @snapshot_group.command(
        name="delete",
        description="permanently delete a snapshot record.",
    )
    async def snapshot_delete(
        self,
        interaction: discord.Interaction,
        snapshot_id: int,
    ):
        deleted = await self.bot.db.delete_snapshot(snapshot_id)
        if deleted:
            await interaction.response.send_message(
                f"╰ *deleted snapshot `#{snapshot_id:03d}`.*", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"*snapshot `#{snapshot_id}` not found.*", ephemeral=True
            )

    @snapshot_group.command(
        name="restore",
        description="recreate missing roles, categories, channels & permission overwrites from a snapshot.",
    )
    async def snapshot_restore(
        self,
        interaction: discord.Interaction,
        snapshot_id: int,
    ):
        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)

        snapshot = await self.bot.db.get_snapshot_by_id(snapshot_id)
        if not snapshot:
            return await interaction.response.send_message(
                f"*snapshot `#{snapshot_id}` not found.*", ephemeral=True
            )

        meta = json.loads(snapshot["metadata_json"])
        embed = kyomi_embed(
            title=f"restore server structure  ·  snapshot `#{snapshot_id:03d}`",
            description=(
                f"**warning:** this action will scan and recreate any missing channels, categories, and roles from `{snapshot['label']}`.\n\n"
                f"╰ **target server:** `{interaction.guild.name}`\n"
                f"╰ **backup elements:** `{meta.get('channels_count', '?')}` channels  ·  `{meta.get('roles_count', '?')}` roles\n"
                f"╰ **mode:** *recreate missing & restore permissions*\n\n"
                "*click confirm below to initiate disaster recovery.*"
            ),
            color=COLOR_AMBER,
            tag="303  •  recovery",
            guild=interaction.guild,
        )
        embed.timestamp = None
        view = ConfirmRestoreView(self, snapshot, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def execute_restore(self, interaction: discord.Interaction, snapshot: dict):
        guild = interaction.guild
        assert guild is not None

        progress_msg = await interaction.followup.send(
            "╰ *disaster recovery started... recreating roles & categories.*",
            ephemeral=True,
        )

        snap_roles = json.loads(snapshot["roles_json"])
        snap_channels = json.loads(snapshot["channels_json"])

        live_roles_by_name = {r.name.lower(): r for r in guild.roles}
        recreated_roles = 0
        role_map = {}  # old_id -> role object

        # 1. Restore missing roles
        for r_data in snap_roles:
            if r_data.get("managed"):
                continue
            r_name = r_data["name"]
            existing = live_roles_by_name.get(r_name.lower())
            if existing:
                role_map[r_data["id"]] = existing
            else:
                try:
                    perms = discord.Permissions(r_data["permissions"])
                    new_role = await guild.create_role(
                        name=r_name,
                        color=discord.Color(r_data["color"]),
                        hoist=r_data["hoist"],
                        permissions=perms,
                        mentionable=r_data["mentionable"],
                        reason="303 kyomi structure restoration",
                    )
                    role_map[r_data["id"]] = new_role
                    recreated_roles += 1
                    await asyncio.sleep(0.3)
                except discord.HTTPException:
                    pass

        # 2. Restore categories first
        category_map = {}  # old_category_id -> category channel object
        live_categories = {c.name.lower(): c for c in guild.categories}
        recreated_categories = 0

        for c_data in [c for c in snap_channels if c["type"] == "category"]:
            c_name = c_data["name"]
            existing_cat = live_categories.get(c_name.lower())
            if existing_cat:
                category_map[c_data["id"]] = existing_cat
            else:
                try:
                    new_cat = await guild.create_category(
                        name=c_name,
                        position=c_data["position"],
                        reason="303 kyomi structure restoration",
                    )
                    category_map[c_data["id"]] = new_cat
                    recreated_categories += 1
                    await asyncio.sleep(0.3)
                except discord.HTTPException:
                    pass

        # 3. Restore channels
        live_channels = {c.name.lower(): c for c in guild.channels if not isinstance(c, discord.CategoryChannel)}
        recreated_channels = 0

        for ch_data in [c for c in snap_channels if c["type"] != "category"]:
            ch_name = ch_data["name"]
            if ch_name.lower() in live_channels:
                continue

            target_category = category_map.get(ch_data["category_id"])

            # Build permission overwrites for this channel
            overwrites = {}
            for ow_data in ch_data.get("overwrites", []):
                target_role = role_map.get(ow_data["target_id"])
                if not target_role:
                    # Try matching by name
                    target_role = discord.utils.get(guild.roles, name=ow_data["target_name"])
                if target_role:
                    allow_perm = discord.Permissions(ow_data["allow"])
                    deny_perm = discord.Permissions(ow_data["deny"])
                    overwrites[target_role] = discord.PermissionOverwrite.from_pair(allow_perm, deny_perm)

            try:
                if ch_data["type"] == "voice":
                    await guild.create_voice_channel(
                        name=ch_name,
                        category=target_category,
                        overwrites=overwrites,
                        bitrate=ch_data.get("bitrate") or 64000,
                        user_limit=ch_data.get("user_limit") or 0,
                        reason="303 kyomi structure restoration",
                    )
                else:
                    await guild.create_text_channel(
                        name=ch_name,
                        category=target_category,
                        overwrites=overwrites,
                        topic=ch_data.get("topic"),
                        slowmode_delay=ch_data.get("slowmode_delay") or 0,
                        nsfw=ch_data.get("nsfw") or False,
                        reason="303 kyomi structure restoration",
                    )
                recreated_channels += 1
                await asyncio.sleep(0.3)
            except discord.HTTPException:
                pass

        finish_embed = kyomi_embed(
            title="disaster recovery completed",
            description=(
                f"╰ **roles restored:** `{recreated_roles}`\n"
                f"╰ **categories restored:** `{recreated_categories}`\n"
                f"╰ **channels recreated:** `{recreated_channels}`\n"
                f"╰ **permissions:** all mapped overwrites applied\n\n"
                f"*server structure has been re-synchronized with snapshot `#{snapshot['id']:03d}`.*"
            ),
            color=COLOR_MINT,
            tag="303  •  recovery",
            guild=guild,
        )
        finish_embed.timestamp = None
        await progress_msg.edit(content=None, embed=finish_embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(SnapshotCog(bot))
