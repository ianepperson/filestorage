from setuptools import setup  # type: ignore

with open('README.md', 'r', encoding='utf-8') as readme:
    long_description = readme.read()


setup(
    name='filestorage',
    version='0.0.1',
    author='Ian Epperson',
    author_email='ian@epperson.com',
    description='foo',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/ianepperson/filestorage',
    packages=['filestorage', 'filestorage.filters', 'filestorage.handlers'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.5',
    platforms='any',
    package_data={
        'filestorage': ['*.pyi', 'py.typed'],
        'filestorage.filters': ['*.pyi', 'py.typed'],
        'filestorage.handlers': ['*.pyi', 'py.typed'],
    },
    include_package_data=True,
    install_requires=['asgiref'],
    extras_require={
        'aio_file': ['aiofiles'],
        's3': ['aioboto3'],
        'test': [
            'pytest',
            'mock',
            'pytest-asyncio',
            'pytest-mock',
            'aioboto3',
            'aiofiles',
        ],
    },
)
