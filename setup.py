"""Setup module for hearth"""

from setuptools import find_packages, setup

setup(
    name="hearth",
    version="0.1.0",
    description="Home Controller",
    url="http://github.com/jonatanolofsson/hearth",
    author="Jonatan Olofsson",
    author_email="jonatan.olofsson@gmail.com",
    license="GPL-3.0",
    packages=find_packages(exclude=['*.tests']),
    entry_points={
        'console_scripts': ['hearth=hearth:main'],
    },
    tests_require=[
        'pytest',
    ],
)
