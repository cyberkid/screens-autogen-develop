# screen-experiments

Screens experimental code, including relevant POCs


# Setup Instructions

Set autogen as the working directory

    > cd autogen

Create virtualenv. See http://docs.python-guide.org/en/latest/dev/virtualenvs/ for installing virtualenv

    > make virtualenv


# Run Instructions

Set autogen as the working directory

    > cd autogen

Activate virtualenv

    > . ~/.virtualenvs/screen/bin/activate

Run the program, eg., to run a test

    > cd autogen/src/test
    > python test_rss_fetcher_gen.py


# Developer Instructions

* When adding a new package that's not installed by default in python, add the requirement to setup.py and 
requirements.txt

* TODO: Add instructions for adding a fetcher

* TODO: Add instructions for adding a furl generator

* TODO: Add instructions for writing and running tests
