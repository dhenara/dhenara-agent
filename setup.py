from setuptools import find_namespace_packages, setup

setup(
    name="dhenara-agent",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src", include=["dhenara.*"]),
    install_requires=[
        "click>=8.0.0",  # CLI
        "pyyaml>=6.0",  # CLI
        "httpx>=0.24.0",
        "requests>=2.25.1",
        "pydantic>=2.0.0",
        "dhenara>=1.0.0",  # Dependency on dhenai
        # TODO_FUTURE: Add a config without observability dependecy
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-instrumentation>=0.40b0",
        "opentelemetry-exporter-otlp>=1.20.0",
        "opentelemetry-exporter-zipkin",
    ],
    extras_require={
        "observability": [
            # Tracing Visualization
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
    description="Dhenara Inc AI-Agent Platform SDK",
    author="Dhenara",
    author_email="support@dhenara.com",
    url="https://github.com/dhenara/dhen-agent",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    # CLI
    entry_points={
        "console_scripts": [
            "dhenara=dhenara.cli:main",
        ],
    },
    # Include template files in the package
    package_data={
        "dhenara.cli": ["templates/**/*"],
    },
    include_package_data=True,
)
