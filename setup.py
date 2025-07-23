import os
import re

from setuptools import find_namespace_packages, setup

version = None
# Read version without importing the package
with open(os.path.join("src/dhenara/agent", "__init__.py")) as f:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string")


setup(
    name="dhenara-agent",
    version=version,
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src", include=["dhenara.*"]),
    install_requires=[
        "dhenara-ai>=1.0.2",
        "click>=8.0.0",  # CLI
        "pyyaml>=6.0",  # CLI
        "httpx>=0.24.0",
        "requests>=2.25.1",
        "pydantic>=2.0.0",
        # Observability dependencies: # TODO_FUTURE: Add a config
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-instrumentation>=0.40b0",
        "opentelemetry-exporter-otlp>=1.20.0",
        "opentelemetry-exporter-zipkin",
    ],
    extras_require={
        "observability": [
            # Additional tracing visualization
            "opentelemetry-exporter-jaeger>=1.20.0",
        ],
        "dev": [
            # Tests
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "pytest-cov>=3.0.0",
        ],
    },
    python_requires=">=3.10",
    description="Dhenara Agent DSL (DAD) Framework SDK",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Dhenara",
    author_email="support@dhenara.com",
    url="https://github.com/dhenara/dhenara-agent",
    license="MIT",
    keywords="ai, llm, machine learning, language models, ai agents, agent frameworks",
    project_urls={
        "Homepage": "https://dhenara.com",
        "Documentation": "https://docs.dhenara.com/",
        "Bug Reports": "https://github.com/dhenara/dhenara-agent/issues",
        "Source Code": "https://github.com/dhenara/dhenara-agent",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
    ],
    # CLI
    entry_points={
        "console_scripts": [
            "dhenara=dhenara.cli:main",
            "dad=dhenara.cli:main",
        ],
    },
    # Include template files in the package
    package_data={
        "dhenara.cli": ["templates/**/*.py"],
    },
    include_package_data=True,
)
