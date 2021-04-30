from setuptools import setup, find_packages
from setuptools.extension import Extension


with open('README.md') as infile:
    long_description = infile.read()


# extensions = [
#     Extension(
#         "DeepVCF.cython_numpy.cython_np_array",
#         ["DeepVCF/cython_numpy/cython_np_array.pyx"],
#         include_dirs=[np.get_include()], # needed for cython numpy to_array
#         # libraries=['',],
#         # library_dirs=['', ], 
#     ),
# ]


setup(
    name='coffee_src',
    version='0.0.1',  # major.minor.maintenance
    description='USDAs database in a flask website',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tmsincomb/coffee-src',
    author='Troy Sincomb',
    author_email='troysincomb@gmail.com',
    license='MIT',
    keywords='coffee app coffee-src',
    packages=find_packages('coffee_src'),
    # include_package_data=True,  # try this out: might be the reason packages didnt break since it wont run without this.
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 1 - ALPHA',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    #  TODO: add classifiers for machine learning/variant caller https://pypi.org/classifiers/
    install_requires=[
        'mysql-connector-python',  # tensoflow production usually lagging in python version compatablity
        'sqlalchemy',
        'pandas',
        'flask',
        'flask-table',
        'flask-wtf',
        'seaborn',
        'geopandas',
        'matplotlib',
        'mapclassify',
    ],
    entry_points={
        'console_scripts': [
            'coffee-src=app:main',
        ],
    },
    # setup_requires=["cython"],
    # ext_modules=cythonize(extensions),  # used for initial build. 
    # ext_modules=extensions,  
)