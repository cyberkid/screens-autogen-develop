#!/usr/bin/env python

from setuptools import setup, find_packages

# hack to fix a Python 2.7.3 issue with multiprocessing module --
# see http://bugs.python.org/issue15881
try:
    import multiprocessing
except ImportError:
    pass

dependencies = [
    # packages for which we want latest stable version
    "pep8>=1.5.6",
    "pylint>=1.2.1",
    "nose>=1.3.2",
    "gevent>=1.0.2",

    # packages to freeze by default
    "beautifulsoup4==4.3.2",
    "pytz==2014.2",
    "timezones==1.7",
    "boto==2.25.0",
    "requests==2.6.0",
    "murl==0.5.1",
    "ujson==1.33",
    "feedparser==5.2.1",
    "lxml==3.6.0",
    "datadog==0.11.0",
    "pyOpenSSL==16.0.0",
    "ndg-httpsclient==0.4.0",
    "pyasn1==0.1.9",
    "python-dateutil==2.5.3",
    "cffi>=1.6.0"
]

setup(
    name="screen generator",
    version="1.0",
    url="https://github.com/quixey/screen-experiments",
    packages=find_packages(),
    install_requires=dependencies
)
