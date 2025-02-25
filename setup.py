from setuptools import find_namespace_packages, setup

setup(
    name="dhenara-agent",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src", include=["dhenara.*"]),
    install_requires=[
        "httpx>=0.24.0",
        "requests>=2.25.1",
        "pydantic>=2.0.0",
        "dhenara-ai>=0.1.0",  # Dependency on dhenai
    ],
    python_requires=">=3.10",
    description="Dhenara Inc AI-Agent Platform SDK",
    author="Dhenara",
    author_email="support@dhenara.com",
    url="https://github.com/dhenara/dhenagent",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
)
