from setuptools import setup

setup(
    name = 'sphinx-git-changelog',
    packages = [
        'sphinx_git_changelog',
    ],
    setup_requires = [
        'setuptools_scm'
    ],
    install_requires = [
        'gitpython',
        'sphinx',
    ],
    use_scm_version = True,
)
