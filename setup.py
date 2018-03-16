"""Setup module for hearth"""
import os
import shutil
from setuptools import find_packages, setup
from setuptools.command.install import install

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class CustomInstallCommand(install):
    """Custom install command."""

    def run(self):
        """Run."""
        install.run(self)
        shutil.copyfile(THIS_DIR + '/hearth.service', '/lib/systemd/system')


setup(
    name="hearth",
    version="0.2.0",
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
    cmdclass={'install': CustomInstallCommand}
)
