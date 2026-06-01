from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="atlas-agent",
    version="0.5.0",
    description="Atlas — The universal AI agent. Voice-first, self-evolving, permanently-memorious.",
    long_description=(Path(__file__).parent / "README.md").read_text(),
    long_description_content_type="text/markdown",
    author="Atlas Team",
    author_email="596600892@qq.com",
    url="https://github.com/596600892/atlas-agent",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "pydantic>=2.0",
        "requests>=2.31",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "ruff>=0.3", "build>=1.0"],
        "voice": [
            "SpeechRecognition>=3.10",
            "pyttsx3>=2.90",
        ],
        "vector": ["sentence-transformers>=2.0"],
        "webui": ["flask>=3.0"],
        "all": [
            "SpeechRecognition>=3.10",
            "pyttsx3>=2.90",
            "sentence-transformers>=2.0",
            "flask>=3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "atlas=atlas_core.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
