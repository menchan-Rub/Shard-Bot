from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional
import logging
from modules.utility.role_service import RoleService

logger = logging.getLogger('utility.role')

class Role(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.role_service = RoleService(bot)

    @app_commands.command(name="createrole", description="新しいロールを作成します")
    @app_commands.describe(
        name="ロール名",
        color="ロールの色（16進数: #RRGGBB）",
        hoist="メンバーリストで別枠表示するかどうか",
        mentionable="メンション可能かどうか",
        reason="作成理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    async def createrole(
        self,
        interaction: discord.Interaction,
        name: str,
        color: Optional[str] = None,
        hoist: Optional[bool] = False,
        mentionable: Optional[bool] = False,
        reason: Optional[str] = None
    ):
        """
        新しいロールを作成します。
        
        Parameters
        ----------
        name : str
            ロール名
        color : str, optional
            ロールの色（16進数）
        hoist : bool, optional
            メンバーリストで別枠表示するかどうか
        mentionable : bool, optional
            メンション可能かどうか
        reason : str, optional
            作成理由
        """
        try:
            # 色を変換
            role_color = None
            if color:
                try:
                    color = color.strip('#')
                    role_color = discord.Color.from_rgb(
                        int(color[0:2], 16),
                        int(color[2:4], 16),
                        int(color[4:6], 16)
                    )
                except ValueError:
                    await interaction.response.send_message(
                        "無効な色形式です。#RRGGBB形式で指定してください。",
                        ephemeral=True
                    )
                    return

            # ロールを作成
            role, message = await self.role_service.create_role(
                guild=interaction.guild,
                name=name,
                color=role_color,
                hoist=hoist,
                mentionable=mentionable,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="ロールを作成しました",
                color=role_color or discord.Color.blue()
            )
            embed.add_field(name="ロール名", value=role.mention, inline=False)
            if role_color:
                embed.add_field(name="色", value=f"#{color}", inline=True)
            embed.add_field(name="別枠表示", value="有効" if hoist else "無効", inline=True)
            embed.add_field(name="メンション可能", value="有効" if mentionable else "無効", inline=True)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "ロールの作成中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to create role: {e}")

    @app_commands.command(name="deleterole", description="ロールを削除します")
    @app_commands.describe(
        role="削除するロール",
        reason="削除理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    async def deleterole(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        reason: Optional[str] = None
    ):
        """
        ロールを削除します。
        
        Parameters
        ----------
        role : discord.Role
            削除するロール
        reason : str, optional
            削除理由
        """
        try:
            # ロールを削除
            message = await self.role_service.delete_role(
                role=role,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="ロールを削除しました",
                color=discord.Color.blue()
            )
            embed.add_field(name="ロール名", value=role.name, inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "ロールの削除中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to delete role: {e}")

    @app_commands.command(name="addrole", description="メンバーにロールを付与します")
    @app_commands.describe(
        member="対象メンバー",
        role="付与するロール",
        reason="付与理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    async def addrole(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
        reason: Optional[str] = None
    ):
        """
        メンバーにロールを付与します。
        
        Parameters
        ----------
        member : discord.Member
            対象メンバー
        role : discord.Role
            付与するロール
        reason : str, optional
            付与理由
        """
        try:
            # ロールを付与
            message = await self.role_service.add_role(
                member=member,
                role=role,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="ロールを付与しました",
                color=discord.Color.blue()
            )
            embed.add_field(name="メンバー", value=member.mention, inline=False)
            embed.add_field(name="ロール", value=role.mention, inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "ロールの付与中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to add role: {e}")

    @app_commands.command(name="removerole", description="メンバーからロールを削除します")
    @app_commands.describe(
        member="対象メンバー",
        role="削除するロール",
        reason="削除理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    async def removerole(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
        reason: Optional[str] = None
    ):
        """
        メンバーからロールを削除します。
        
        Parameters
        ----------
        member : discord.Member
            対象メンバー
        role : discord.Role
            削除するロール
        reason : str, optional
            削除理由
        """
        try:
            # ロールを削除
            message = await self.role_service.remove_role(
                member=member,
                role=role,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="ロールを削除しました",
                color=discord.Color.blue()
            )
            embed.add_field(name="メンバー", value=member.mention, inline=False)
            embed.add_field(name="ロール", value=role.mention, inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "ロールの削除中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to remove role: {e}")

    @app_commands.command(name="modifyrole", description="ロールの設定を変更します")
    @app_commands.describe(
        role="変更するロール",
        name="新しいロール名",
        color="新しい色（16進数: #RRGGBB）",
        hoist="メンバーリストで別枠表示するかどうか",
        mentionable="メンション可能かどうか",
        reason="変更理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    async def modifyrole(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        name: Optional[str] = None,
        color: Optional[str] = None,
        hoist: Optional[bool] = None,
        mentionable: Optional[bool] = None,
        reason: Optional[str] = None
    ):
        """
        ロールの設定を変更します。
        
        Parameters
        ----------
        role : discord.Role
            変更するロール
        name : str, optional
            新しいロール名
        color : str, optional
            新しい色（16進数）
        hoist : bool, optional
            メンバーリストで別枠表示するかどうか
        mentionable : bool, optional
            メンション可能かどうか
        reason : str, optional
            変更理由
        """
        try:
            # 色を変換
            role_color = None
            if color:
                try:
                    color = color.strip('#')
                    role_color = discord.Color.from_rgb(
                        int(color[0:2], 16),
                        int(color[2:4], 16),
                        int(color[4:6], 16)
                    )
                except ValueError:
                    await interaction.response.send_message(
                        "無効な色形式です。#RRGGBB形式で指定してください。",
                        ephemeral=True
                    )
                    return

            # ロールを更新
            message = await self.role_service.modify_role(
                role=role,
                name=name,
                color=role_color,
                hoist=hoist,
                mentionable=mentionable,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="ロールを更新しました",
                color=role_color or role.color
            )
            embed.add_field(name="ロール", value=role.mention, inline=False)
            if name:
                embed.add_field(name="新しい名前", value=name, inline=True)
            if color:
                embed.add_field(name="新しい色", value=f"#{color}", inline=True)
            if hoist is not None:
                embed.add_field(name="別枠表示", value="有効" if hoist else "無効", inline=True)
            if mentionable is not None:
                embed.add_field(name="メンション可能", value="有効" if mentionable else "無効", inline=True)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "ロールの更新中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to modify role: {e}")

    @app_commands.command(name="roles", description="サーバーのロール一覧を表示します")
    @app_commands.guild_only()
    async def roles(self, interaction: discord.Interaction):
        """サーバーのロール一覧を表示します"""
        try:
            # ロール一覧を取得
            roles = await self.role_service.list_roles(interaction.guild)
            
            # ロールを表示
            embed = discord.Embed(
                title=f"{interaction.guild.name} のロール一覧",
                color=discord.Color.blue()
            )

            # ロールを25個ずつに分割して表示
            chunks = [roles[i:i + 25] for i in range(0, len(roles), 25)]
            for i, chunk in enumerate(chunks, 1):
                value = "\n".join([
                    f"{role.mention} - {len(role.members)}メンバー"
                    for role in reversed(chunk)
                    if not role.is_default()
                ])
                if value:
                    embed.add_field(
                        name=f"ロール一覧 {i}",
                        value=value,
                        inline=False
                    )

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "ロール一覧の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to list roles: {e}")

    @app_commands.command(name="roleinfo", description="ロールの詳細情報を表示します")
    @app_commands.describe(
        role="情報を表示するロール"
    )
    @app_commands.guild_only()
    async def roleinfo(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """
        ロールの詳細情報を表示します。
        
        Parameters
        ----------
        role : discord.Role
            情報を表示するロール
        """
        try:
            # ロール情報を取得
            info = await self.role_service.get_role_info(role)

            # 権限を文字列に変換
            permissions = []
            for perm, value in discord.Permissions(info['permissions']):
                if value:
                    permissions.append(perm)

            # 情報を表示
            embed = discord.Embed(
                title=f"ロール情報: {info['name']}",
                color=info['color']
            )
            embed.add_field(name="ID", value=info['id'], inline=True)
            embed.add_field(name="メンバー数", value=info['member_count'], inline=True)
            embed.add_field(name="色", value=str(info['color']), inline=True)
            embed.add_field(name="位置", value=info['position'], inline=True)
            embed.add_field(name="別枠表示", value="有効" if info['hoist'] else "無効", inline=True)
            embed.add_field(name="メンション可能", value="有効" if info['mentionable'] else "無効", inline=True)
            embed.add_field(name="システム管理", value="有効" if info['managed'] else "無効", inline=True)
            embed.add_field(name="作成日時", value=info['created_at'].strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)

            if permissions:
                embed.add_field(
                    name="権限",
                    value="\n".join([f"✓ {perm}" for perm in permissions]),
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "ロール情報の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get role info: {e}")

    @createrole.error
    @deleterole.error
    @addrole.error
    @removerole.error
    @modifyrole.error
    async def role_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """ロールコマンドのエラーハンドリング"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "このコマンドを実行する権限がありません。",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "コマンドの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Error in role command: {error}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Role(bot)) 