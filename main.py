from re import template
from flask import Flask, render_template, request, Markup
import logging
import sys

from covid_data_handler import schedule_covid_updates, update_covid_data, check_covid_updates, remove_task
from covid_news_handling import news_API_request, config_file, json, parse_news_csv, check_news_updates, remove_article, schedule_news_updates

# set up logs
log = logging.getLogger(__name__)
FORMAT= '%(levelname)s: %(asctime)s %(message)s'
logging.basicConfig(format=FORMAT, stream=sys.stdout, level=logging.DEBUG)

# set up flask
app = Flask(__name__, template_folder="templates")

global config_error
config_error = False
global image_url
image_url = "set_in_config"
global favicon_url
favicon_url = "set_in_config"
global config_location
config_location = "set_in_config"
global config_nation
config_nation = "set_in_config"

global local_last7days_cases
local_last7days_cases = 0
global national_last7days_cases
national_last7days_cases = 0
global articles_list
articles_list = []
global national_hospital_cases
national_hospital_cases = 0
global national_deaths
national_deaths = 0
global updates_list
updates_list = []

def read_config() -> None:
    '''
        Open config file to read contents
    '''
    
    global image_url
    global favicon_url
    global config_location
    global config_nation
    try:
        with open(config_file, 'r') as json_file:
            json_data = json.loads(json_file.read())
            image_url = json_data['imagePath']
            favicon_url = json_data['faviconPath']
            config_location = json_data['location']
            config_nation = json_data['nation']
            logging.debug('Successfully read configuration file')

    except IOError:
        logging.error('Problem opening %s, check to make sure your configuration file is not missing.'
            , config_file)
        global config_error
        config_error = True

read_config()

@app.route('/')
def home():
    '''
        Main function to populate HTML template with data, gets most recent Covid
        statistics, process and then display them. Calls news_api_request function 
        to get a list of news articles for display. 
    '''
    global local_covid_dict
    global config_location
    global config_nation
    global articles_list
    global local_last7days_cases
    global national_last7days_cases
    global national_hospital_cases
    global national_deaths
    global updates_list

    # detect config_error, without config, images can't be displayed
    if config_error == True:
        print("Error reading configuration file! Please make sure configuration file is set up correctly!")
        exit()

    local_last7days_cases, local_hospitalCases, local_total_deaths = update_covid_data("local")
    national_last7days_cases, national_hospital_cases, national_deaths = update_covid_data("nation")

    ''' AYO WHY IN HTML HAVE BUT SO SNEAKY
    local_hospitalCases = "Hospital Cases: " + str(hospitalCases)
    local_total_deaths = "Total Deaths: " + str(total_deaths)'''

    # get news updates
    news_API_request()
    articles_dict = parse_news_csv()

    # put news articles in a list
    for news in articles_dict:
        line = articles_dict[news]
        articles_list.append(line)

    # render index.html with params to populate the site with data
    return render_template('index.html', title="Covid Updates",
            favicon = favicon_url,
            image = image_url, location = config_location,
            local_7day_infections = local_last7days_cases,
            nation_location = config_nation,
            national_7day_infections = national_last7days_cases,
            news_articles = articles_list,
            updates = updates_list,
            hospital_cases = national_hospital_cases,
            deaths_total = national_deaths)


@app.route('/index', methods=['GET'])
def parse_url():
    '''
        Gets all the parameters from the URL and processes it to schedule data
        and for news updates
    '''
    global articles_list
    global local_last7days_cases
    global national_last7days_cases
    global national_hospital_cases
    global national_deaths

    # if the user's first landing is at the /index page,
    # redirect to home() function
    if articles_list == []:
        home()

    # get all arguments from url
    time = request.args.get('update')
    label = request.args.get('two')
    repeat = request.args.get('repeat')
    covid_data = request.args.get('covid-data')
    news = request.args.get('news')
    notif = request.args.get('notif')
    update_item = request.args.get('update_item')

    # change data into bool 
    if repeat is not None:
        repeat = True
    else:
        repeat = False

    if covid_data is not None:
        covid_data = True
    else:
        covid_data = False

    if news is not None:
        news = True
    else:
        news = False

    # handles when there are no ticked boxes
    if repeat == False and covid_data == False and news == False:
        log.warning("No boxes ticked!")
        exit()

    # get task status
    log.debug("printing updates_list ")

    # check for outdated scheds
    check_covid_updates(updates_list)
    check_news_updates(updates_list)

    # update page with data after automatic page refreshes
    if (repeat == False and covid_data == False and news == False and time == None 
        and label == None and notif == None and update_item == None):

        log.debug("Getting data updates")
        # get local and national COVID 19 statistics
        local_last7days_cases, local_hospitalCases, local_total_deaths = update_covid_data("local")
        national_last7days_cases, national_hospital_cases, national_deaths = update_covid_data("nation")

        # get news updates
        news_API_request()
        articles_dict = parse_news_csv()

        # put news articles in a list
        for each_news in articles_dict:
            line = articles_dict[each_news]
            articles_list.append(line)

    if time != None and label != None:
        # store event details in a list to keep track of it
        index_content = Markup(time + "<br>Repeat: " + str(repeat) + "<br>Covid Data Updates: "
            + str(covid_data) + "<br>News updates: " + str(news))

        line = {'title':label,'content':index_content}
        updates_list.append(line)

        if covid_data == True:
            schedule_covid_updates(time, label, repeat)
        if news == True:
            schedule_news_updates(time, label, repeat)

    log.debug(" updates list: %s", updates_list)

    if notif != None:
        log.debug("Calling remove_article func, key: %s", notif)
        articles_list = remove_article(notif)

    if update_item != None:
        log.debug("Calling remove_task func, key: %s", update_item)
        remove_task(update_item)
        print("lmao")

    # render index.html with params to populate the site with data
    return render_template('index.html', title="Covid Updates",
            favicon = favicon_url,
            image = image_url, location = config_location,
            local_7day_infections = local_last7days_cases,
            nation_location = config_nation,
            national_7day_infections = national_last7days_cases,
            news_articles = articles_list,
            updates = updates_list,
            hospital_cases = national_hospital_cases,
            deaths_total = national_deaths)

if __name__ == '__main__':
    app.run(debug=True)
