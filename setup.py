from setuptools import setup, find_packages

setup(
    name="k2spicedb",
    version="0.1.0",
    description="A tool to migrate Keycloak realms to SpiceDB schemas",
    author="James Staud",
    author_email="james@example.com",
    url="https://github.com/Jstaud/k2spicedb",
    packages=find_packages(),
    install_requires=[
        "argparse==1.4.0",
        "json==2.0.9"
    ],
    entry_points={
        "console_scripts": [
            "k2spicedb=k2spicedb.cli:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
