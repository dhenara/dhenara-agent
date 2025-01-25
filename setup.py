from setuptools import setup, find_namespace_packages, find_packages


setup(
    name="dhenara",
    version="0.1.0",
    package_dir={"": "src"},  # Tell setuptools packages are under src
    # packages=find_namespace_packages(where="src"),  # Find all packages under src
    packages=find_packages(where="src"),  # Finds all packages under src
    install_requires=[
        "httpx>=0.24.0",
        "requests>=2.25.1",
        "pydantic>=2.0.0",
    ],
    python_requires=">=3.10",
    description="Dhenara Inc AI Platform SDK",
    author="Dhenara",
    author_email="support@dhenara.com",
    # url="https://github.com/dhenara/sdk-python",
    classifiers=[
        "Programming Language :: Python :: 3",
        # "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
