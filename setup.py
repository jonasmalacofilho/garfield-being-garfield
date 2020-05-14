import setuptools

HOME = 'https://github.com/jonasmalacofilho/pookys-diary'
VERSION = '0.0.2'

setuptools.setup(
    name='pookys-diary',
    version=VERSION,
    author='Jonas Malaco',
    author_email='me @at@ jonasmalaco .dot. com',
    description='A PyQt5 experiment, possibly made by, for or with Pooky',
    url=HOME,
    packages=setuptools.find_packages(),
    install_requires=['pyqt5', 'requests', 'appdirs'],
    python_requires='>=3.6',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'pookys-diary=pooky.diary:main',
        ],
    },
)
