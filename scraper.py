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

def addFile(filename):
    with connection.cursor() as cursor:
        query = "insert into files values(null,'"+str(project)+"','"+str(filename)+"');"
        try:
            cursor.execute(query)
        except Exception as e:
            print(e)

def fileId_ifexists(filename):
    with connection.cursor() as cursor:
        query='select idfiles from files where filepath_on_coverity ="'+filename+'";'
        cursor.execute(query)
        result=cursor.fetchone()
        if result and 'idfiles' in result.keys():
            return result['idfiles']
        return None
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
time.sleep(90)  # reasonable?

def get_filepath(soup):
    filepath=soup.find_all("ul",{"id":"source-viewer-file-path"})
    if len(filepath)>1:
        print("more than one file path found. logic error")
        return None
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
        raise Exception('more than one table found under occurrences')
    elif len(tables) == 0:
        print("no occurrence data? source code purged? last_defect_id logic will be ruined. exiting")
        raise Exception('no table found under occurrences')
    elif len(tables) == 1:
        table = tables[0]

    # parse table
    events = table.find_all("tr", {"class": ["event-tree-node ng-scope","event-tree-node ng-scope selected"]})
    names = table.find_all("span", {"class": "event-tag event-name ng-binding"})
    files = table.find_all("td", {"class": "event-tree-filename ng-binding"})
    event_list=[]
    name_list=[]
    short_filename_list=[]
    filepath_list=[]

    element_id=1
    for e in events:
        #find the next row, starts from 2 for this function to work
        element_id+=1
        selenium_element=driver.find_element_by_xpath("/html/body/div[2]/aside/div/div[2]/div/div[6]/div/div/div/table/tbody/tr["+str(element_id)+"]")
        driver.execute_script("arguments[0].scrollIntoView();", selenium_element)
        defect_id = e["data-merged-defect-id"]

        #get the event (occurrence) id
        event_id = str(e["data-event-id"])
        event_id=event_id.split("-")
        event_id=event_id[1]
        event_list.append(event_id)

        #click on it to get the full filepath
        try:
            driver.execute_script("arguments[0].click();",selenium_element)
        except:
            print("cannot click on events?")
            driver.execute_script("arguments[0].click();",selenium_element)

        time.sleep(3)

        #get the fullpath. null if there's any problem in it.
        soup = BS(driver.page_source, features="html.parser")
        filepath = get_filepath(soup)
        if filepath==None:
            filepath="null"
        filepath=filepath.strip()
        filepath_list.append(filepath)

    #event detail
    for n in names:
        name_list.append(n.text)

    #filename and line number
    for f in files:
        short_filename_list.append(f.text)

    #insert into database
    print(len(event_list),len(name_list),len(short_filename_list),len(filepath_list))
    if not (len(event_list)==len(name_list) and len(name_list)==len(short_filename_list) and len(short_filename_list)==len(filepath_list)):
        print("logic error...red alert... exiting",defect_id) 
        raise Exception("all 4 lists are not equal.")
    for i in range (0,len(event_list)):
        with connection.cursor() as cursor:
            ## first look for the alert id
            query="select idalerts from alerts where cid="+str(defect_id)+" and stream='"+str(project)+"';"
            cursor.execute(query)
            result=cursor.fetchone()
            alert_id=result["idalerts"]

            ## now split short filename and line count
            temp=short_filename_list[i].split(":")
            short_filename=temp[0]
            line_number=temp[1]

            ## now look for the file_id
            ### 3 possibilities
            if filepath_list[i]=="null":
                file_id="null"
            else:
                #do a sanity check if shot filename and full filepath matches
                ## can't match becuase of web page not updating in time
                temp=filepath_list[i].split("/")
                if temp[-1]== short_filename:
                    if fileId_ifexists(filepath_list[i])==None:
                        addFile(filepath_list[i])
                    file_id=fileId_ifexists(filepath_list[i])
                else:
                    file_id="null"

            ## insert into occurrences
            query="insert into occurrences values("+str(alert_id)+","+ \
            str(defect_id)+","+str(event_list[i])+ ",'" + str(short_filename) + "'," + \
            str(file_id)+","+str(line_number)+");"
            try:
                print(query)
                cursor.execute(query)
            except Exception as e:
                print(e)
    return defect_id

last_defect_id=None
for page in range(0, pagelimit):
    # first_cid = driver.find_element_by_xpath(
    #     "/html/body/div[2]/div[3]/div[1]/div[2]/div[1]/div[5]/div/div[1]")
    # first_cid.click()
    # time.sleep(3)
    # # find occurrences data
    # soup = BS(driver.page_source, features="html.parser")
    # occurrences = soup.find_all("div", {"class": "occurrences-data"})
    # occurrences = occurrences[0]
    # tables = occurrences.find_all("table")
    # defect_id = None
    # try:
    #     defect_id = read_table(driver, tables)
    #     last_defect_id = defect_id #if it's the first iteration, last_defect_id will remain None
    # except Exception as e:
    #     print("reading table did not work.", e)
    #     #TODO what to do here?

    while True:
        #find the next cid and click on it
        next_cid = driver.find_element_by_xpath(
            "/html/body/div[2]/div[3]/div[1]/div[2]/div[1]/div[5]/div/div[1]")
        driver.execute_script("arguments[0].scrollIntoView();", next_cid)
        try:
            next_cid.click()
        except:
            next_cid.click()
        time.sleep(3)

        soup = BS(driver.page_source, features="html.parser")

        #check if this alert id has been already handled
        temp = soup.find_all("tr", {"class": ["event-tree-node ng-scope","event-tree-node ng-scope selected"]})
        if len(temp)==0:
            print("logic error. no cid found in occurrence table ")
            continue
        temp=temp[0]
        try:
            defect_id=temp["data-merged-defect-id"]
        except Exception as e:
            print("cannot find defect_id.",e)
            continue
        with connection.cursor() as cursor:
            query="select idalerts from alerts where cid="+str(defect_id)+" and stream='"+str(project)+"';"
            cursor.execute(query)
            result=cursor.fetchone()
            alert_id=result["idalerts"]
            query="select * from occurrences where alert_id="+str(alert_id)
            cursor.execute(query)
            result=cursor.fetchall()
        if len(result)>0:
            print("alert id already exists",defect_id,alert_id)
            continue
        else:
            print("new alert id found: ",defect_id,alert_id)

        ### Note that the code will only come up to this point if
        ### the defect id is updated

        occurrences = soup.find_all("div", {"class": "occurrences-data"})
        occurrences = occurrences[0]
        tables = occurrences.find_all("table")
        try:
            read_table(driver, tables)
        except Exception as e:
            print("reading table did not work.", e)
        if (defect_id == last_defect_id):
            print("page end reached",defect_id)
            #click on to next page and break this while loop
            next_page=driver.find_elements_by_class_name("ui-state-default ui-corner-all ui-icon-container")
            next_page=next_page[1] # assuming there will always be two corner button
            next_page.click()
            time.sleep(90)
            break
        else:
            last_defect_id = defect_id
