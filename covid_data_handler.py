'''
This module contains functions to retrieve and handle COVID-19 statistics

'''
import logging
import csv
import json
import time
import sys
import traceback
from datetime import datetime
import threading
from uk_covid19 import Cov19API


log = logging.getLogger(__name__)
FORMAT= '%(levelname)s: %(asctime)s %(message)s'
logging.basicConfig(format=FORMAT, stream=sys.stdout, level=logging.DEBUG)

config_file = 'covid_config.cfg'

global glocation
glocation = "Exeter"
global glocation_type
glocation_type = "ltla"
global exclude_list
exclude_list = []
global config_location
config_location = "set_in_config"
global config_nation
config_nation = "set_in_config"
global sched_covid
sched_covid = []
global sched_news
sched_news = []
global loop
loop = True
global threads
threads = []
global covid_sched_list
covid_sched_list = []

def read_config() -> None:
    '''
        Open config file to read contents
    '''
    global config_location
    global config_nation

    try:
        with open(config_file, 'r') as json_file:
            # Get the necessary data from the configuraton file
            json_data = json.loads(json_file.read())
            config_location = json_data['location']
            config_nation = json_data['nation']
            logging.debug('Successfully read configuration file')
    except IOError:
        # Catch an IOError exception
        logging.error('Problem opening %s, ' +
                'check to make sure your configuration file is not missing.', config_file)
        exit()

read_config()

def parse_csv_data(csv_filename: str) -> dict:
    '''
        Takes filename as argument, opens and reads the csv file,
        returns file content as a dictionary
    '''
    # open csv file in read mode
    logging.debug("Opening %s for reading", csv_filename)
    reader = csv.DictReader(open(csv_filename, "r"))

    # initialize dict and index
    big_dict = {}
    index = 0

    # loop through the csv.DictReader
    for index, i in enumerate(reader):
        # assign each row to a big_dict to create a dictionary of dictionaries
        big_dict[index] = i
    logging.debug("Successfully read from %s into dictionary", csv_filename)

    return big_dict

# TEST FUNCTION FOR ^ FAIL
def test_parse_csv_data():
    '''
        Test function for parse_csv_data
    '''
    data = parse_csv_data("nation_2021-10-28.csv")
    assert len(data) == 639

# DONE I THINK
def process_covid_data(covid_csv_data: dict) -> tuple[int, int, int]:
    '''
        Takes in a dict, process the data to calculate and return
        last7days_cases, hospitalCases and total_deaths
    '''

    # get case numbers from the last 7 days
    dataset = covid_csv_data

    last7days_cases = 0
    last7_index = 0

    # initialize data, checking before calculating
    logging.debug("Calculating statistics for last 7 days cases")
    cases = dataset[last7_index]['newCasesBySpecimenDate']
    date_check = dataset[last7_index]['date']

    # loop through empty cells and skip 2021-10-27 due to incomplete data
    while (cases == '') or (date_check == '2021-10-27'):
        last7_index += 1
        cases = dataset[last7_index]['newCasesBySpecimenDate']
        date_check = dataset[last7_index]['date']

    # total up the case numbers
    for i in range(last7_index, last7_index+7):
        cases = dataset[i]['newCasesBySpecimenDate']
        last7days_cases = last7days_cases + int(cases)

    logging.debug("Retrieving statistics for most recent hospital cases")
    # initialize counter
    hos_index = 0

    # while cell is empty, continue loop
    while (dataset[hos_index]['hospitalCases']) == '' and hos_index < (len(dataset)-1):
        # add to the index counter and reassign data
        hos_index += 1
    hospitalCases = dataset[hos_index]['hospitalCases']

    logging.debug("Retrieving statistics for total deaths")
    # set death_index to top most row
    death_index = 0

    # loop through empty cells, adding index after every loop
    while ((dataset[death_index]['cumDailyNsoDeathsByDeathDate']) == ''
            and death_index < (len(dataset)-1)):
        # add to the index counter and reassign data
        death_index += 1
    total_deaths = covid_csv_data[death_index]['cumDailyNsoDeathsByDeathDate']


    if last7days_cases == '':
        last7days_cases = 0
    if hospitalCases == '':
        hospitalCases = 0
    if total_deaths == '':
        total_deaths = 0


    logging.debug("Last 7 days: %s, Hospital cases: %s, Total deaths: %s."+
        "End of process_covid_data func", last7days_cases, hospitalCases, total_deaths)

    # convert strings to int and return
    return (last7days_cases, hospitalCases, total_deaths)


def test_process_covid_csv_data():
    '''
        Test function for process_covid_csv_data
    '''
    last7days_cases, current_hospital_cases, total_deaths = process_covid_data(
            parse_csv_data("nation_2021-10-28.csv"))
    assert last7days_cases == 240_299
    assert current_hospital_cases == 7019
    assert total_deaths == 141544


def covid_API_request(location: str = "Exeter", location_type: str = "ltla") -> str:
    '''
        Takes location and location type as variable, get latest Covid
        statistics using the Covid19API
    '''

    save_location = location.lower() + "_covid_data.csv"

    # setup area filter
    logging.info("Setting up location filter and structure for covid statistics API request")
    location_filter = ['areaType=' + location_type,'areaName=' + location]

    # setup the structure of how we want to receive the data
    cases_by_location = {
        "areaCode": "areaCode",
        "areaName": "areaName",
        "areaType": "areaType",
        "date": "date",
        "cumDailyNsoDeathsByDeathDate":"cumDailyNsoDeathsByDeathDate",
        "hospitalCases": "hospitalCases",
        "newCasesBySpecimenDate": "newCasesBySpecimenDate"
    }

    # initialize Cov19API object
    api = Cov19API(filters=location_filter, structure=cases_by_location)

    # extract data
    try:
        logging.debug("Retrieving data from ukcovid19 API")
        api.get_json()
    except Exception as e:
        logging.error("Error retrieving data from ukcovid19 API, %s", traceback.format_exc())

    api.get_csv(save_as=save_location)
    logging.debug("Successfully retrieved and saved API data as CSV, %s", save_location)

    return save_location


def update_covid_data(loc_type: str) -> tuple[int,int,int]:
    '''
        Sets different parameters according to the location_type argument
        Then retrieves COVID 19 statistics from CSV to process the data
        Returns a tuple of data ready for display on the template
    '''
    if loc_type == "local":
        logging.info("Retrieving latest Covid19 statistics for %s, location type: ltla"
            , config_location)
        file_name = covid_API_request(location=config_location, location_type='ltla')

    elif loc_type == "nation":
        logging.info("Retrieving latest Covid19 statistics for %s, location type: nation"
            , config_nation)
        file_name = covid_API_request(location=config_nation, location_type='nation')

    else:
        logging.critical("Invalid location type (%s), should be either local or nation", loc_type)
        exit()

    last7days_cases, hospitalCases, total_deaths = process_covid_data(parse_csv_data(file_name))
    logging.debug("Successfully retrieved COVID 19 statistics")
    return (last7days_cases, hospitalCases, total_deaths)


def schedule_covid_updates(update_interval, update_name: str, *repeat) -> None:
    '''
        This function takes in arguments and schedules a COVID-19
        statistics update according to the time provided.
    '''

    global config_location
    global config_nation
    global covid_sched_list


    logging.debug("Converting user time input (%s) to seconds since epoch", update_interval)
    # process time from arguments and split it into 2 variables
    update_hours, update_minutes = map(int, update_interval.split(':'))
    # get update time in seconds
    update_time_in_seconds = (update_hours * 60 * 60) + (update_minutes * 60)

    # set up current date and time as variables for comparison
    current_date_time = datetime.now()
    temp_time = time.time()

    # Get HH:MM time format from the current time
    current_time = datetime.fromtimestamp(temp_time).strftime('%H:%M')

    # Split hours and minutes into 2 variables
    curr_hours, curr_minutes = map(int, current_time.split(':'))

    # Get current time in seconds
    curr_time_in_seconds = (curr_hours * 60 * 60) + (curr_minutes * 60)

    logging.debug("Initializing Covid sched function")

    # Check if time has past then sets the date accordingly
    if curr_time_in_seconds < update_time_in_seconds:
        day = current_date_time.day
    else:
        day = current_date_time.day + 1

    # Set update time into datetime type for processing
    update_date_time = datetime(current_date_time.year, current_date_time.month,
        day, update_hours, update_minutes)

    date_time_diff = update_date_time-current_date_time
    time_diff_seconds = date_time_diff.total_seconds()

    task1 = threading.Timer(time_diff_seconds, update_covid_data("local"))
    task2 = threading.Timer(time_diff_seconds, update_covid_data("nation"))
    task1.daemon = True
    task2.daemon = True
    task1.start()
    task2.start()

    # store thread details in a list of dicts
    temp1 = {'update_name':update_name, 'task':task1}
    temp2 = {'update_name':update_name, 'task':task2}
    covid_sched_list.append(temp1)
    covid_sched_list.append(temp2)

    logging.debug("Sucessfully added %s and %s to threading queue", task1, task2)

    # recursive loop
    if repeat is True:
        time_diff_seconds = time_diff_seconds + 86400
        new_update_interval = datetime.fromtimestamp(time_diff_seconds).strftime('%c')
        schedule_covid_updates(new_update_interval, update_name, True)


def check_covid_updates(displayed_updates_list: list) -> list:
    '''
        This function accepts updates_list as an argument and
        performs comparisons with the threading queue to check
        for threads that have already been executed.

        Remove executed threads from updates_list
    '''

    log.debug("Checking for expired updates")


    global covid_sched_list
    del_index_list = []

    # check if list is not empty then loop through it
    if displayed_updates_list != []:
        for index, each in enumerate(displayed_updates_list):
            match = 0
            name_search = each['title']
            for line in covid_sched_list:
                # cross reference with thread dict from schedule_news_updates function
                log.debug("Search key: %s, Current: %s", name_search, line['update_name'])
                if name_search == line['update_name']:
                    # look through thread queue to find matches
                    for thread in threading.enumerate():
                        log.debug(thread,line['task'])
                        # thread hasn't been executed yet, removal not required
                        if thread == line['task']:
                            match += 1
                    # no match = thread executed, add index to a list for removal
                    if match == 0:
                        del_index_list.append(index)

        # remove outdated lists
        for every in del_index_list:
            del displayed_updates_list[every]
    else:
        log.debug("Updates list is empty")

    log.debug("Returned updates list: %s", displayed_updates_list)