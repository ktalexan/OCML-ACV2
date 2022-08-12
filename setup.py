from setuptools import distribution, setup
from versiontag import cache_git_tag, get_version

# Make sure versiontag exists before going any further. This won't actually install the package. It will just download the egg file into `.eggs` so that it can be used henceforth in setup.py.
Distribution().fetch_build_eggs('versiontag')

# Import versiontag components from

# This caches for version in version.txt, so that it is still accessible if the .git folder disappears, for example, after the slug is built on Heroku.
cache_git_tag()

# If you want to use versiontag anywhere outside of the setup.py script, you should also add it to `install requires`. This makes sure to actually install it, instead of just downloading the egg.
install_requires = [''' 'versiontag>1.2.0' ''']

setup(
    name="OCML-ACV2"
    version="3.0"
    description="Orange County Machine Learning Repository: Azure Cognitive Vision Photosphere Object Classification"
    author="Kostas Alexandridis, PhD, GISP"
    author_email="Kostas.Alexandridis@ocpw.ocgov.com"
    packages=[ocml-acv]  # same as name
    install_requires=[''' 'versiontag>1.2.0' ''']
)
