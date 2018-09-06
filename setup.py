from setuptools import setup, find_packages
setup(
    name='dxl-learn',
    version='0.1.3',
    description='Machine learn library.',
    url='https://github.com/Hong-Xiang/dxlearn',
    author='Hong Xiang',
    author_email='hx.hongxiang@gmail.com',
    license='MIT',
    namespace_packages=['dxl'],
    packages=find_packages('src/python'),
    package_dir={'': 'src/python'},
    install_requires=['dxl-fs', 'click', 'dxl-shape',
                      'dxl-core',
                      'arrow', 'tqdm'],
    entry_points="""
        [console_scripts]
        learn=dxl.learn.cli.main:dxlearn
    """,
    zip_safe=False)
