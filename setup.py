from setuptools import setup

setup(
    name="email_printer",
    version="1.0.0",
    py_modules=["email_printer"],
    install_requires=[
        "python-dotenv>=0.19.0",
        "PyGObject>=3.40.0"
    ],
    entry_points={
        'console_scripts': [
            'email-printer=email_printer:main',
        ],
    },
) 