from setuptools import setup, find_packages

setup(
    name="shard-bot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "discord.py",
        "python-dotenv",
        "PyYAML",
        "Pillow",
        "aiohttp",
    ],
) 