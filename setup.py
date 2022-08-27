from setuptools import setup
import psg

setup(
    name='pilgrim_syntax_generator',
    version=psg.__version__,
    description="Text generator",
    url='https://github.com/JoshuaEnglish/psg',
    author='Josh English',
    author_email='josh@joshuarenglish.com',
    license = 'GNU3',
    packages = ['psg',],
    install_requires=['lxml'],
    zip_safe=False,
    entry_points={
        'console_scripts': ['psg=psg.cli:main'],
    }
)
