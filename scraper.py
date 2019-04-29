'''selenium scraping for coverity database'''
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as BS
from selenium.webdriver.common.action_chains import ActionChains
import os
import requests
import time
import pymysql
import sys
import math

connection = pymysql.connect(host='localhost', user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

#this variables will be provided as cmd arguments
# project = "Kodi"
#for Kodi = "https://scan5.coverity.com/reports.htm#v51575/p10258"
#for ovirt - https://scan6.coverity.com/reports.htm#v43456/p10291
#for firefox - https://scan5.coverity.com/reports.htm#v51570/p10098
project= sys.argv[1]
url=sys.argv[2]
ignore_pages=int(sys.argv[3])
sleep_per_page=int(sys.argv[4])

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
    wait = WebDriverWait(driver, 60)
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
time.sleep(sleep_per_page)  

def get_filepath(soup):
    #very conservative. even if we don't get the full filepath. No big deal. 
    # # Well some deal obviously
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
def read_table(driver, tables, defect_id,alert_id,main_fid):

    if len(tables) > 1:
        print("more than one table found? logic error")
        raise Exception('more than one table found under occurrences')
    elif len(tables) == 0:
        print("no occurrence data? source code purged? last_defect_id logic will be ruined. exiting")
        raise Exception('no table found under occurrences')
    elif len(tables) == 1:
        table = tables[0]
    
    #now take only the first tbody
    ## as other tbody may indicate example of similar cases and other stuffs

    tbodies=table.find_all("tbody")
    if len(tbodies) == 0:
        raise Exception('no tbody found under occurrences')
    table=tbodies[0]

    #now we should only have the event history
    
    # parse table
    defect_events = table.find_all("tr", {"class":"event-tree-node ng-scope selected"})
    events = table.find_all("tr", {"class": ["event-tree-node ng-scope","event-tree-node ng-scope selected"]})
    names = table.find_all("span", {"class": "event-tag event-name ng-binding"})
    files = table.find_all("td", {"class": "event-tree-filename ng-binding"})

    #the main event with a diamond alert sign
    defect_event_id=None
    if len(defect_events)>0:
        defect_event_id=defect_events[0]
        defect_event_id=defect_event_id["data-event-id"]
        defect_event_id=defect_event_id.split('-')
        defect_event_id=defect_event_id[1]

    event_list=[]
    name_list=[]
    short_filename_list=[]
    filepath_list=[]

    element_id=1
    for e in events:
        #find the next row, starts from 2 for this function to work
        element_id+=1
        selenium_element=driver.find_element_by_xpath('//*[@id="source-browser-defect-occurrences"]/div/div/div/table/tbody[1]/tr['+str(element_id)+"]")
        driver.execute_script("arguments[0].scrollIntoView();", selenium_element)

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
            try:
                driver.execute_script("arguments[0].click();",selenium_element)
            except:
                print("could not execute js click")

        time.sleep(1)

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
            ## get full filepath for main fid
            query="select filepath_on_coverity from files where idfiles="+str(main_fid)
            cursor.execute(query)
            result=cursor.fetchone()
            main_filepath=result["filepath_on_coverity"]

            ## now split short filename and line count
            temp=short_filename_list[i].split(":")
            short_filename=temp[0]
            short_filename=connection.escape_string(short_filename)
            line_number=temp[1]

            ## now look for the file_id
            ### 3 possibilities
            if filepath_list[i]=="null":
                file_id="null"
            else:
                #do a sanity check if short filename and full filepath matches
                ## can't match becuase of web page not updating in time
                temp=filepath_list[i].split("/")
                if temp[-1]== short_filename:
                    if fileId_ifexists(filepath_list[i])==None:
                        addFile(filepath_list[i])
                    file_id=fileId_ifexists(filepath_list[i])
                else:
                    file_id="null"
            
            # if file_id is null, try to guess file_id here
            if file_id=="null":
                ###check if source code purged or short filename matches main file path
                if short_filename==main_filepath.split("/")[-1]:
                    file_id=main_fid
                else:
                    query='select * from files where filepath_on_coverity like "%/'+short_filename+'" and project = "'+project+'";'
                    cursor.execute(query)
                    results=cursor.fetchall()
                    if len(results)==1:
                        file_id=results[0]["idfiles"] 
                    #else manually verify?

            ## insert into occurrences
            query="insert into occurrences values("+str(alert_id)+","+ \
            str(defect_id)+","+str(event_list[i])+ ",'" + str(short_filename) + "'," + \
            str(file_id)+","+str(line_number)+",0);"
            try:
                print(query)
                cursor.execute(query)
            except Exception as e:
                print(e)

    with connection.cursor() as cursor:
        if defect_event_id!=None:
            query="update occurrences set is_defect_line=1 \
                where alert_id="+str(alert_id)+" and cid="+str(defect_id)+ \
                " and event_id="+str(defect_event_id)+";"
            try:
                print(query)
                cursor.execute(query)
            except Exception as e:
                print(e)


#get all the cids from this project
cids=[]
aids=[]
fids=[]
with connection.cursor() as cursor:
    query="select * from alerts where stream='"+project+"' order by cid desc;"
    cursor.execute(query)
    results=cursor.fetchall()
    for item in results:
        cids.append(str(item["cid"]))
        aids.append(str(item["idalerts"]))
        fids.append(str(item["file_id"]))

pagelimit=int(math.ceil(float(len(cids))/200.0))

for page in range(0, pagelimit):
    #look for if we need to ignore any page 
    if ignore_pages > 0:
        ignore_pages -= 1
        next_page=driver.find_element_by_xpath('//*[@id="details-pager"]/div/span/span[5]')
        next_page.click()
        time.sleep(sleep_per_page)
        continue
    
    #wait for cids[page*200] visibility
    wait_cid=cids[page*200]
    wait_cid=driver.find_element_by_xpath("//*[contains(text(), '"+wait_cid+"')]")
    wait.until(EC.visibility_of_element_located(wait_cid))
    for index in range(page*200,(page+1)*200):
        defect_id=cids[index]
        next_cid=driver.find_element_by_xpath("//*[contains(text(), '"+defect_id+"')]")
        driver.execute_script("arguments[0].scrollIntoView();", next_cid)
        try:
            next_cid.click()
        except:
            time.sleep(3)
            print("clicking did not happen?")
            #driver.execute_script("window.scrollTo("+str(next_cid.location['x'])+","+str(next_cid.location['y'])+")")
            ActionChains(driver).move_to_element(next_cid).click().perform()
        
        time.sleep(1)
    
        soup = BS(driver.page_source, features="html.parser")

        #check if data has alreade been parsed
        alert_id=aids[index]
        with connection.cursor() as cursor:
            query="select * from occurrences where alert_id="+str(alert_id)
            cursor.execute(query)
            result=cursor.fetchall()
        if len(result)>0:
            print("alert id already exists",defect_id,alert_id)
            continue
        else:
            print("new alert id found: ",defect_id,alert_id)

        occurrences = soup.find_all("div", {"class": "occurrences-data"})
        if len(occurrences) != 1:
            print("logic errorwith occurrences... exiting")
            exit()
        occurrences = occurrences[0] #there should be only one. And always there should be one.
        tables = occurrences.find_all("table")
        try:
            file_id=fids[index]
            read_table(driver, tables, defect_id, alert_id,file_id)
        except Exception as e:
            print("reading table did not work.", e)
    next_page=driver.find_element_by_xpath('//*[@id="details-pager"]/div/span/span[5]')
    next_page.click()
    time.sleep(sleep_per_page)