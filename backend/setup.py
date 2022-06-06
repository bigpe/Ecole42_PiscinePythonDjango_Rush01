from pip._internal.req import parse_requirements
from setuptools import setup

install_reqs = parse_requirements('requirements.txt', session='install')

reqs = [str(ir.requirement) for ir in install_reqs]

setup(
    install_requires=reqs
)
