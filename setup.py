import setuptools

with open('README.md', 'r', encoding='utf8') as f:
    long_description = f.read()

setuptools.setup(
    name='django-rest-base',
    version='0.1.0',
    url='https://github.com/devluci/django-rest-base',
    author='Lucid (@devluci)',
    author_email='contact@lucid.dev',
    description='Customized features and environment for building a Django REST framework app.',
    license='MIT',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(exclude=[
        'rest_base.conf.app_template',
    ]),
    include_package_data=True,
    python_requires='>=3.8',
    install_requires=[
        'Django>=3.0',
        'djangorestframework>=3.10',
    ],
    extras_require={
        'jwt': ['PyJWT'],
        'channels': ['channels'],
        'sentry': ['sentry-sdk'],
        'random': ['numpy'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Topic :: Internet :: WWW/HTTP',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Framework :: Django',
        'Framework :: Django :: 3.0',
    ],
)
