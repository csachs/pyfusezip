from setuptools import setup, find_packages

setup(
    name='pyfusezip',
    version='0.0.1',
    description='Simple and fast read-only ZIP file mount using Python and FUSE',
    long_description='see https://github.com/csachs/pyfusezip',
    author='Christian C. Sachs',
    author_email='sachs.christian@gmail.com',
    url='https://github.com/csachs/pyfusezip',
    packages=find_packages(),
    requires=['fuse'],
    entry_points=dict(console_scripts=['pyfusezip = pyfusezip.pyfusezip:main']),
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ]
)

