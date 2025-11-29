from setuptools import setup, find_packages

setup(
    name="transit",
    version="0.1.0",
    description="TransIt - Document translation with ultra-precise structure preservation",
    author="TransIt Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "python-docx>=1.2.0",
        "openai>=1.12.0",
        "tenacity>=8.2.0",
        "tqdm>=4.66.0",
        "click>=8.1.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "transit=transit.cli:main",
        ],
    },
    python_requires=">=3.10",
)
