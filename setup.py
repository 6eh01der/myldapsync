###############################################################################
#
# myldapsync - adopted for MySQL fork of pgldapsync by EnterpriseDB Corporation
#
# Synchronise MySQL users with users in an LDAP directory.
#
###############################################################################

"""myldapsync package creation."""

import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

# Get the requirements list for the current version of Python
    with open('requirements.txt', 'r', encoding='utf-8') as reqf:
        required = reqf.read().splitlines()

setuptools.setup(
    name="myldapsync",
    version="1.0.4",
    author="Artur Lebedev",
    author_email="ras_atari@mail.ru",
    description="Synchronise LDAP users to MySQL and MariaDB",
    license='MySQL',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/6eh01der/myldapsync",
    packages=setuptools.find_packages(),
    install_requires=required,
    python_requires='>=3.8',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['myldapsync=myldapsync.__init__:main'],
    },
    include_package_data=True
)
