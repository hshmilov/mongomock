from setuptools import setup


setup(
    name='axonius_exports',
    version='0.0.1',
    author='Axonius',
    py_modules=['axonius_exports'],
    entry_points={
        'console_scripts': [
            'axonius_exports=axonius_exports:main',
        ],
    },
)
