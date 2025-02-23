import numpy as np
import matplotlib.pyplot as plt
import io
from typing import Dict, List, Optional, Tuple, Union
import re
import logging
from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.calculator')

class CalculatorService:
    def __init__(self):
        """計算サービスを初期化します"""
        # 単位変換の定義
        self.length_units = {
            'm': 1,
            'km': 1000,
            'cm': 0.01,
            'mm': 0.001,
            'in': 0.0254,
            'ft': 0.3048,
            'yd': 0.9144,
            'mi': 1609.344
        }
        
        self.weight_units = {
            'kg': 1,
            'g': 0.001,
            'mg': 0.000001,
            'lb': 0.45359237,
            'oz': 0.028349523125
        }
        
        self.volume_units = {
            'l': 1,
            'ml': 0.001,
            'gal': 3.78541178,
            'qt': 0.946352946
        }

        self.temperature_conversions = {
            'c_to_f': lambda x: x * 9/5 + 32,
            'f_to_c': lambda x: (x - 32) * 5/9,
            'c_to_k': lambda x: x + 273.15,
            'k_to_c': lambda x: x - 273.15,
            'f_to_k': lambda x: (x - 32) * 5/9 + 273.15,
            'k_to_f': lambda x: (x - 273.15) * 9/5 + 32
        }

    async def evaluate_expression(self, expression: str) -> str:
        """
        数式を評価します。
        
        Parameters
        ----------
        expression : str
            評価する数式
            
        Returns
        -------
        str
            計算結果
        """
        try:
            # 安全な評価のために使用できる関数を制限
            allowed_names = {
                'sin': np.sin,
                'cos': np.cos,
                'tan': np.tan,
                'asin': np.arcsin,
                'acos': np.arccos,
                'atan': np.arctan,
                'sqrt': np.sqrt,
                'log': np.log,
                'log10': np.log10,
                'exp': np.exp,
                'pi': np.pi,
                'e': np.e,
                'abs': abs,
                'pow': pow
            }

            # 数式を評価
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            
            # 結果を整形
            if isinstance(result, (int, float)):
                return f"{result:g}"
            else:
                return str(result)

        except Exception as e:
            logger.error(f"Expression evaluation failed: {e}")
            raise ValueError("無効な数式です")

    async def convert_unit(
        self,
        value: float,
        from_unit: str,
        to_unit: str,
        unit_type: str
    ) -> float:
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
            単位の種類（length, weight, volume, temperature）
            
        Returns
        -------
        float
            変換結果
        """
        try:
            if unit_type == 'temperature':
                # 温度の変換
                conversion_key = f"{from_unit}_to_{to_unit}"
                if conversion_key in self.temperature_conversions:
                    return self.temperature_conversions[conversion_key](value)
                raise ValueError("無効な温度単位です")

            # その他の単位変換
            units = {
                'length': self.length_units,
                'weight': self.weight_units,
                'volume': self.volume_units
            }

            if unit_type not in units:
                raise ValueError("無効な単位タイプです")

            unit_dict = units[unit_type]
            if from_unit not in unit_dict or to_unit not in unit_dict:
                raise ValueError("無効な単位です")

            # 基準単位に変換してから目的の単位に変換
            base_value = value * unit_dict[from_unit]
            result = base_value / unit_dict[to_unit]
            return result

        except Exception as e:
            logger.error(f"Unit conversion failed: {e}")
            raise

    async def calculate_statistics(self, numbers: List[float]) -> Dict[str, float]:
        """
        基本的な統計量を計算します。
        
        Parameters
        ----------
        numbers : List[float]
            計算対象の数値リスト
            
        Returns
        -------
        Dict[str, float]
            統計量の辞書
        """
        try:
            return {
                'mean': float(np.mean(numbers)),
                'median': float(np.median(numbers)),
                'std': float(np.std(numbers)),
                'min': float(np.min(numbers)),
                'max': float(np.max(numbers)),
                'count': len(numbers)
            }
        except Exception as e:
            logger.error(f"Statistics calculation failed: {e}")
            raise

    async def generate_graph(
        self,
        x_data: List[float],
        y_data: List[float],
        title: str = "グラフ",
        x_label: str = "X軸",
        y_label: str = "Y軸",
        graph_type: str = "line"
    ) -> io.BytesIO:
        """
        グラフを生成します。
        
        Parameters
        ----------
        x_data : List[float]
            X軸のデータ
        y_data : List[float]
            Y軸のデータ
        title : str
            グラフのタイトル
        x_label : str
            X軸のラベル
        y_label : str
            Y軸のラベル
        graph_type : str
            グラフの種類（line, scatter, bar）
            
        Returns
        -------
        io.BytesIO
            生成されたグラフの画像データ
        """
        try:
            plt.figure(figsize=(10, 6))
            plt.title(title)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            plt.grid(True)

            if graph_type == "line":
                plt.plot(x_data, y_data)
            elif graph_type == "scatter":
                plt.scatter(x_data, y_data)
            elif graph_type == "bar":
                plt.bar(x_data, y_data)
            else:
                raise ValueError("無効なグラフタイプです")

            # グラフをバイトデータとして保存
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            logger.error(f"Graph generation failed: {e}")
            raise

    async def parse_function(
        self,
        function_str: str,
        x_range: Tuple[float, float],
        points: int = 100
    ) -> Tuple[List[float], List[float]]:
        """
        関数文字列を解析してグラフ用のデータを生成します。
        
        Parameters
        ----------
        function_str : str
            関数の文字列表現（例: "x**2 + 2*x + 1"）
        x_range : Tuple[float, float]
            X軸の範囲
        points : int
            生成するポイント数
            
        Returns
        -------
        Tuple[List[float], List[float]]
            X座標とY座標のリスト
        """
        try:
            # 安全な評価のために使用できる関数を制限
            allowed_names = {
                'sin': np.sin,
                'cos': np.cos,
                'tan': np.tan,
                'asin': np.arcsin,
                'acos': np.arccos,
                'atan': np.arctan,
                'sqrt': np.sqrt,
                'log': np.log,
                'log10': np.log10,
                'exp': np.exp,
                'pi': np.pi,
                'e': np.e,
                'abs': abs,
                'pow': pow
            }

            # X座標を生成
            x = np.linspace(x_range[0], x_range[1], points)
            
            # 関数を評価
            f = lambda x: eval(function_str, {"__builtins__": {}, "x": x}, allowed_names)
            y = f(x)

            return x.tolist(), y.tolist()

        except Exception as e:
            logger.error(f"Function parsing failed: {e}")
            raise ValueError("無効な関数式です") 