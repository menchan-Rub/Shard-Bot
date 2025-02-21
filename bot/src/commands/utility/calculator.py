from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional, List
import re
import logging
from ...modules.utility.calculator_service import CalculatorService

logger = logging.getLogger('utility.calculator')

class Calculator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.calculator_service = CalculatorService()

    @app_commands.command(name="calc", description="数式を計算します")
    @app_commands.describe(
        expression="計算する数式（例: 2 + 2, sin(pi/2), sqrt(16)）"
    )
    async def calc(
        self,
        interaction: discord.Interaction,
        expression: str
    ):
        """
        数式を計算します。
        
        Parameters
        ----------
        expression : str
            計算する数式
        """
        try:
            result = await self.calculator_service.evaluate_expression(expression)
            
            embed = discord.Embed(
                title="計算結果",
                color=discord.Color.blue()
            )
            embed.add_field(name="数式", value=f"`{expression}`", inline=False)
            embed.add_field(name="結果", value=f"`{result}`", inline=False)
            
            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "計算中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Calculation failed: {e}")

    @app_commands.command(name="convert", description="単位を変換します")
    @app_commands.describe(
        value="変換する値",
        from_unit="変換元の単位",
        to_unit="変換先の単位",
        unit_type="単位の種類（length, weight, volume, temperature）"
    )
    async def convert(
        self,
        interaction: discord.Interaction,
        value: float,
        from_unit: str,
        to_unit: str,
        unit_type: str
    ):
        """
        単位を変換します。
        
        Parameters
        ----------
        value : float
            変換する値
        from_unit : str
            変換元の単位
        to_unit : str
            変換先の単位
        unit_type : str
            単位の種類
        """
        try:
            result = await self.calculator_service.convert_unit(
                value=value,
                from_unit=from_unit.lower(),
                to_unit=to_unit.lower(),
                unit_type=unit_type.lower()
            )
            
            embed = discord.Embed(
                title="単位変換結果",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="変換前",
                value=f"`{value} {from_unit}`",
                inline=True
            )
            embed.add_field(
                name="変換後",
                value=f"`{result:g} {to_unit}`",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "単位変換中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Unit conversion failed: {e}")

    @app_commands.command(name="stats", description="基本的な統計量を計算します")
    @app_commands.describe(
        numbers="計算対象の数値（カンマ区切り）"
    )
    async def stats(
        self,
        interaction: discord.Interaction,
        numbers: str
    ):
        """
        基本的な統計量を計算します。
        
        Parameters
        ----------
        numbers : str
            計算対象の数値（カンマ区切り）
        """
        try:
            # 数値リストを解析
            number_list = [
                float(num.strip())
                for num in numbers.split(',')
                if num.strip()
            ]
            
            if not number_list:
                await interaction.response.send_message(
                    "数値を入力してください。",
                    ephemeral=True
                )
                return

            # 統計量を計算
            stats = await self.calculator_service.calculate_statistics(number_list)
            
            embed = discord.Embed(
                title="統計結果",
                color=discord.Color.blue()
            )
            embed.add_field(name="データ数", value=f"`{stats['count']}`", inline=True)
            embed.add_field(name="平均", value=f"`{stats['mean']:g}`", inline=True)
            embed.add_field(name="中央値", value=f"`{stats['median']:g}`", inline=True)
            embed.add_field(name="標準偏差", value=f"`{stats['std']:g}`", inline=True)
            embed.add_field(name="最小値", value=f"`{stats['min']:g}`", inline=True)
            embed.add_field(name="最大値", value=f"`{stats['max']:g}`", inline=True)
            
            await interaction.response.send_message(embed=embed)

        except ValueError:
            await interaction.response.send_message(
                "無効な数値が含まれています。",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "統計計算中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Statistics calculation failed: {e}")

    @app_commands.command(name="plot", description="関数のグラフを生成します")
    @app_commands.describe(
        function="関数式（例: x**2 + 2*x + 1）",
        x_min="X軸の最小値",
        x_max="X軸の最大値",
        title="グラフのタイトル"
    )
    async def plot(
        self,
        interaction: discord.Interaction,
        function: str,
        x_min: float = -10,
        x_max: float = 10,
        title: Optional[str] = None
    ):
        """
        関数のグラフを生成します。
        
        Parameters
        ----------
        function : str
            関数式
        x_min : float
            X軸の最小値
        x_max : float
            X軸の最大値
        title : str, optional
            グラフのタイトル
        """
        await interaction.response.defer()

        try:
            # データを生成
            x_data, y_data = await self.calculator_service.parse_function(
                function_str=function,
                x_range=(x_min, x_max)
            )

            # グラフを生成
            graph_title = title or f"y = {function}"
            buf = await self.calculator_service.generate_graph(
                x_data=x_data,
                y_data=y_data,
                title=graph_title,
                x_label="x",
                y_label="y"
            )

            # 画像を送信
            file = discord.File(buf, filename="graph.png")
            embed = discord.Embed(
                title="関数グラフ",
                color=discord.Color.blue()
            )
            embed.set_image(url="attachment://graph.png")
            
            await interaction.followup.send(file=file, embed=embed)

        except ValueError as e:
            await interaction.followup.send(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                "グラフの生成中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Graph generation failed: {e}")

    @app_commands.command(name="units", description="利用可能な単位の一覧を表示します")
    async def units(self, interaction: discord.Interaction):
        """利用可能な単位の一覧を表示します"""
        embed = discord.Embed(
            title="利用可能な単位",
            color=discord.Color.blue()
        )

        # 長さの単位
        length_units = ", ".join(sorted(self.calculator_service.length_units.keys()))
        embed.add_field(
            name="長さ (length)",
            value=f"`{length_units}`",
            inline=False
        )

        # 重さの単位
        weight_units = ", ".join(sorted(self.calculator_service.weight_units.keys()))
        embed.add_field(
            name="重さ (weight)",
            value=f"`{weight_units}`",
            inline=False
        )

        # 体積の単位
        volume_units = ", ".join(sorted(self.calculator_service.volume_units.keys()))
        embed.add_field(
            name="体積 (volume)",
            value=f"`{volume_units}`",
            inline=False
        )

        # 温度の単位
        embed.add_field(
            name="温度 (temperature)",
            value="`c (摂氏), f (華氏), k (ケルビン)`",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Calculator(bot)) 