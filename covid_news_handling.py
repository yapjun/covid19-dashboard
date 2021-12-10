'''
This module contains functions that uses NewsAPI to retrieve news articles
and processes the data and save it in a CSV
'''
import json
import time
import requests, csv
import pandas as pd
from datetime import datetime
import threading
import logging
import sys


log = logging.getLogger(__name__)
FORMAT= '%(levelname)s: %(asctime)s %(message)s'
logging.basicConfig(format=FORMAT, stream=sys.stdout, level=logging.DEBUG)


global covid_search
gcovid_search = "Covid COVID-19 coronavirus"

# config file name
config_file = 'covid_config.cfg'
global config_error
config_error = False
global apiKey
apiKey = "set_in_config"
global exclude_list
exclude_list = []
global threads
threads = []
global news_dict
news_dict = {}
global news_csv
news_csv = "set_in_config"
global news_sched_list
news_sched_list = []

everything_news_url = 'https://newsapi.org/v2/everything'

def read_config() -> None:
    global apiKey
    global news_csv
    try:
        with open(config_file, 'r') as json_file:
            json_data = json.loads(json_file.read())
            config_api = json_data['apiKey']
            apiKey = "&apiKey=" + config_api
            news_csv = json_data['newsCSV']
            logging.debug('Successfully read configuration file')
    except IOError:
        logging.error('Problem opening %s, '+
            'check to make sure your configuration file is not missing.', config_file)
        global config_error
        config_error = True

read_config()

def news_API_request(covid_terms: str = "Covid COVID-19 coronavirus") -> dict:
    '''
        Takes in search terms separated by space delimiter,
        gets the latest news with terms as query, converts results to a CSV file
    '''

    if config_error is False:
        # update global variable definition for use in between functions
        global gcovid_search
        gcovid_search = covid_terms

        # split the words into a list using space as a delimiter
        keywords = covid_terms.split()

        # initialize query
        query = "?qInTitle=" + keywords[0]

        # loop through the list to get all keywords for the search query
        for i in range(1,len(keywords)):
            query = query + "+OR+" + keywords[i]

        # concatenate query to exclude articles that have been removed
        # only runs when list is not empty
        if exclude_list != []:
            query = query + "+NOT+" + exclude_list[0]
            # loop through entire list, add every item to the query
            for i in range(1,len(exclude_list)):
                query = query + "+NOT+" + exclude_list[i]

        # build url
        url = (everything_news_url + query + apiKey)

        # get response from NewsAPI
        response = requests.get(url)
        logging.info("Successfully received a response from NewsAPI")

        # process json file
        response_json_string = json.dumps(response.json())
        response_dict = json.loads(response_json_string)


        # get the articles only
        articles_list = response_dict['articles']

        # format and convert to CSV
        df = pd.json_normalize(articles_list)
        df.to_csv('covid_news.csv', header=True, index=True, index_label="index")

        logging.info("Converted NewsAPI json to %s. End of news_API_request func", news_csv)
    else:
        logging.error("Error reading configuration file")

    return articles_list


def parse_news_csv() -> dict:
    '''
        Open CSV file of news articles and
        return as a dictionary of articles
    '''

    # open csv file in read mode
    try:
        reader = csv.DictReader(open(news_csv, "r"))
        logging.debug("Reading from %s", news_csv)
    except IOError:
        logging.error("Error opening %s", news_csv)

    # initialize dict and index
    big_dict = {}
    index = 0

    # loop through the csv.DictReader
    for index, i in enumerate(reader):
        # assign each row to a big_dict to create a dictionary of dictionaries
        big_dict[index] = i

    logging.info("Successfully read %s to a dictionary", news_csv)
    return big_dict


def remove_article(title: str) -> dict:
    '''
        This function takes a news article title as and argument
        and removes it from the list of articles. Removed articles
        will not show up in future news updates.
    '''
    global exclude_list

    # add argument to list of exclusions
    exclude_list.append(title)
    
    # get data from news csv file
    news_dict = parse_news_csv()
    dict_size = len(news_dict)

    # loop through dict to find title matches
    logging.debug("Finding title matches to remove article. Searching for: %s" + title)

    for i in range(0,dict_size):
        if news_dict[i]['title'] == title:
            del news_dict[i]
            logging.info("Successfully deleted index %s, %s from list!", i, title)

            # reassign dict size
            dict_size = len(news_dict)

            # loop to fix indexes
            logging.debug("Fixing indexes")
            for j in range (i+1, dict_size+1):
                current_index = int(news_dict[j]['index'])
                news_dict[j]['index'] = current_index - 1
            break

    logging.info("Writing updated articles list to %s", news_csv)
    list_of_dicts = []
    for each in news_dict:
        line = news_dict[each]
        list_of_dicts.append(line)

    keys = list_of_dicts[0].keys()

    with open(news_csv, 'w', newline='') as csv_output:
        dict_writer = csv.DictWriter(csv_output, keys)
        dict_writer.writeheader()
        dict_writer.writerows(list_of_dicts)
    logging.info("%s has been updated", news_csv)

    return list_of_dicts


def update_news() -> dict:
    '''
        To be used with schedule_news_updates function,
        Calls all the necessary functions for a news update
        Returns data as a dictionary
    '''

    logging.info("Updating news")
    news_API_request()
    news_dict =  parse_news_csv()
    logging.info("Retrieved latest news")

    print("update_news function was ran at " + str(time.time()))
    return news_dict


def schedule_news_updates(update_interval, update_name: str, *repeat) -> None:
    '''
        This function accepts update_interval and update_name as argument,
        Creates a thread to execute at the time provided to call for a news
        update
    '''

    global exclude_list
    global threads
    global news_sched_list

    # process time from arguments and split it into 2 variables
    logging.debug("Converting user time input (%s) to seconds since epoch", update_interval)
    update_hours, update_minutes = map(int, update_interval.split(':'))

    # calculate and get update time in seconds for the day
    update_time_in_seconds = (update_hours * 60 * 60) + (update_minutes * 60)

    # set up current date and time as variables for comparison
    current_date_time = datetime.now()
    temp_time = time.time()

    # Get HH:MM time format from the current time
    current_time = datetime.fromtimestamp(temp_time).strftime('%H:%M')

    # Split hours and minutes into 2 variables
    curr_hours, curr_minutes = map(int, current_time.split(':'))

    # Get current time in seconds since Epoch
    curr_time_in_seconds = (curr_hours * 60 * 60) + (curr_minutes * 60)

    # Check if time has past then sets the date accordingly
    if curr_time_in_seconds < update_time_in_seconds:
        day = current_date_time.day
    else:
        day = current_date_time.day + 1

    # Set update time into datetime type for processing
    update_date_time = datetime(current_date_time.year, 
        current_date_time.month, day, update_hours, update_minutes)
    date_time_diff = update_date_time-current_date_time
    time_diff_seconds = date_time_diff.total_seconds()

    task = threading.Timer(time_diff_seconds, update_news)
    task.daemon = True
    task.start()

    # store thread details in a list of dicts
    temp = {'update_name':update_name, 'task':task}
    news_sched_list.append(temp)

    logging.debug("Sucessfully added %s to threading queue", task)

    # recursive loop
    if repeat is True:
        # 1 day is added to the time
        time_diff_seconds = time_diff_seconds + 86400
        new_update_interval = datetime.fromtimestamp(time_diff_seconds).strftime('%c')
        schedule_news_updates(new_update_interval, update_name, True)


def check_news_updates(displayed_updates_list: list) -> None:
    '''
        This function accepts updates_list as an argument and
        performs comparisons with the threading queue to check
        for threads that have already been executed.

        Remove executed threads from updates_list
    '''

    log.debug("Checking for expired updates")


    global news_sched_list
    del_index_list = []

    # check if list is not empty then loop through it
    if displayed_updates_list != []:
        for index, each in enumerate(displayed_updates_list):
            match = 0
            name_search = each['title']
            for line in news_sched_list:
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
