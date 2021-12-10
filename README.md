# COVID Dashboard

The COVID 19 Dashboard application retrieves the latest news from NewsAPI and COVID-19 statistics from the Public Health England API. Data updates can be scheduled by the user on any time of the day.

## Prerequisites
Python version 3.9.9 is needed, it can be downloaded from the official [Python.org](https://www.python.org/downloads/release/python-399/) website.


## Module Installations
Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the prerequisites for the COVID dashboard.

These are the modules that are required for the app: 
- pandas
- flask
- requests
- uk_covid19
- threading


*For example:*

```bash
pip install flask
pip install pandas
```

## Getting Started

After installing the prerequisites, you will need to setup the configuration file. Open up the covid_config.cfg file and enter your API key, image paths and others. 

This COVID 19 Dashboard does not support location and nations outside of the UK.

## Usage
After setting up the covid_config.cfg file, you're all set! If you have an IDE, you may use that to open up main.py and try running the COVID-19 dashboard. 

Or you may run main.py from your operating system's command line.
First, you will need to get the file path to main.py. To do that, go to your file location and find main.py, then right-click on it and click on Properties. You will find a 'Location' segment on the Properties window. Copy the entire file path.

- Open up command-line
- Type `cd` with a space, then paste the file location and hit enter
- Type `python3 main.py` and hit enter
- Open up any browser and enter this in the URL `http://127.0.0.1:5000/`

Now you can schedule your own news and updates whenever you want to! 

## Author
Daphne Yap Jun Yi

