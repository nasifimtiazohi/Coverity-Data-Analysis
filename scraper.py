from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as BS
import os
import requests
import time
import pymysql

connection = pymysql.connect(host='localhost',
                             user='root',
                             db='890coverity',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

#this variables will be provided as cmd arguments
project = "Kodi"
url = "https://scan5.coverity.com/reports.htm#v51540/p10258"
pagelimit = 16

# To prevent download dialog (not needed) ?
def prevent_download_dialogue(driver):
    profile = webdriver.FirefoxProfile()
    profile.set_preference('browser.download.folderList', 2)  # custom location
    profile.set_preference('browser.download.manager.showWhenStarting', False)
    profile.set_preference('browser.download.dir', '/tmp')
    profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'text/csv')

# sign in to coverity scan
try:
    
    driver = webdriver.Firefox()
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 10)
    driver.get("https://scan.coverity.com/users/sign_in")
    driver.find_element_by_xpath(
        '//*[@id="content-for-fixed-navbar"]/div[2]/div/div/div[2]/div[1]/a').click()
    driver.find_element_by_id('login_field').send_keys('nasifimtiaz88@gmail.com')
    driver.find_element_by_id('password').send_keys(os.environ['gitpass'])
    driver.find_element_by_name('commit').click()
except:
    print("can't sign in")

# goes to specific project
driver.find_element_by_link_text(project).click()
view_defect = driver.find_element_by_xpath(
    "/html/body/div[1]/div[2]/div/div/div[3]/div/p[1]/a")
driver.execute_script("arguments[0].target='_self';", view_defect)
view_defect.click()
time.sleep(3)
driver.get(url)
time.sleep(60)  # reasonable?

def get_filepath(soup):
    filepath=soup.find_all("ul",{"id":"source-viewer-file-path"})
    if len(filepath)>1:
        print("more than one file path found. logic error")
    elif len(filepath)==0:
        return None
    elif len(filepath)==1:
        filepath=filepath[0]
    spans=filepath.find_all("span")
    span=spans[0]
    try:
        return span["title"]
    except:
        return None
def read_table(driver, tables):
    defect_id = None

    if len(tables) > 1:
        print("more than one table found? logic error")
    elif len(tables) == 0:
        print("no occurrence data? source code purged? last_defect_id logic will be ruined. exiting")
        exit()
    elif len(tables) == 1:
        table = tables[0]

    # parse table
    events = table.find_all("tr", {"class": "event-tree-node ng-scope"})
    names = table.find_all("span", {"class": "event-tag event-name ng-binding"})
    files = table.find_all("td", {"class": "event-tree-filename ng-binding"})
    if len(events)==len(names) and len(names)==len(files):
        print("logic error... exiting")
    
    
    event_list=[]
    name_list=[]
    file_list=[]
    filepath_list=[]
    for e in events:
        driver.execute_script("arguments[0].scrollIntoView();", next_cid)

        defect_id = e["data-merged-defect-id"]

        event_id = str(e["data-event-id"])
        event_id=event_id.split("-")
        event_id=event_id[1]
        try:
            e.click()
        except:
            e.click()

        soup = BS(driver.page_source, features="html.parser")
        filepath = get_filepath(soup)
        if filepath==None:
            filepath="null"
        filepath_list.append(filepath)

        event_list.append(event_id)

    for n in names:
        name_list.append(n.text)

    for f in files:
        file_list.append(f.text)

    #insert into database
    with connection.cursor() as cursor:
        query="insert into occurrences values("+str(defect_id)+","+str(event_id)+ \
            ","+
    return defect_id


for page in range(0, pagelimit):
    first_cid = driver.find_element_by_xpath(
        "/html/body/div[2]/div[3]/div[1]/div[2]/div[1]/div[5]/div/div[1]")
    first_cid.click()
    time.sleep(5)
    # find occurrences data
    soup = BS(driver.page_source, features="html.parser")
    occurrences = soup.find_all("div", {"class": "occurrences-data"})
    occurrences = occurrences[0]
    tables = occurrences.find_all("table")
    res = open("res.txt", "w")
    defect_id = None
    try:
        defect_id = read_table(driver, tables)
    except Exception as e:
        print("failed", e)

    last_defect_id = defect_id
    while True:
        next_cid = driver.find_element_by_xpath(
            "/html/body/div[2]/div[3]/div[1]/div[2]/div[1]/div[5]/div/div[1]")
        driver.execute_script("arguments[0].scrollIntoView();", next_cid)
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "/html/body/div[2]/div[3]/div[1]/div[2]/div[1]/div[5]/div/div[1]")))
        try:
            next_cid.click()
        except:
            next_cid.click()
        time.sleep(3)
        print("next one")
        soup = BS(driver.page_source, features="html.parser")
        occurrences = soup.find_all("div", {"class": "occurrences-data"})
        occurrences = occurrences[0]
        tables = occurrences.find_all("table")
        try:
            defect_id = read_table(driver, tables)
        except Exception as e:
            print("failed here", e)
        if (defect_id == last_defect_id):
            res.write("page end reached")
            # TODO goto next page
            break
        else:
            last_defect_id = defect_id
    break  # temp
