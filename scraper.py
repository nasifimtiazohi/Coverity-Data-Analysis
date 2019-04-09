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

connection = pymysql.connect(host='localhost',
                             user='root',
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
pagelimit = int(sys.argv[3])
ignore_pages=int(sys.argv[4])
alerts_per_page=200
sleep_per_page=int(sys.argv[5])

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
def read_table(driver, tables, defect_id):

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

    #the main event with a diamond alert sign :P :P
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
        #selenium_element=driver.find_element_by_xpath("/html/body/div[2]/aside/div/div[2]/div/div[6]/div/div/div/table/tbody/tr["+str(element_id)+"]")
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
            ## first look for the alert id
            query="select idalerts, file_id from alerts where cid="+str(defect_id)+" and stream='"+str(project)+"';"
            cursor.execute(query)
            result=cursor.fetchone()
            alert_id=result["idalerts"]
            main_fid=result["file_id"]

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
                ###check if source code purged
                if len(event_list)==1 and line_number == 1 and short_filename in main_filepath:
                    file_id=main_fid
                ### check if short filename matches main file path
                else:
                    temp=main_filepath.split("/")
                    temp=temp[-1]
                    if short_filename== temp:
                        file_id=main_fid
                    else:
                        query='select * from files where filepath_on_coverity like "%'+short_filename+'" and project = "'+project+'";'
                        cursor.execute(query)
                        results=cursor.fetchall()
                        if len(results)==1:
                            file_id=results[0]["idfiles"] 

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


for page in range(0, pagelimit):
    #look for if we need to ignore any page 
    if ignore_pages > 0:
        ignore_pages -= 1
        next_page=driver.find_element_by_xpath('//*[@id="details-pager"]/div/span/span[5]')
        next_page.click()
        time.sleep(sleep_per_page)
        continue

    last_selection="ui-widget-content slick-row active even selected"
    unique_alerts=[]
    while True:
        #find the next cid and click on it 
        next_cid = driver.find_element_by_xpath(
            '/html/body/div[2]/div[3]/div[1]/div[2]/div[1]/div[5]/div/div[1]')
        driver.execute_script("arguments[0].scrollIntoView();", next_cid)
        #driver.execute_script("window.scrollTo("+str(next_cid.location['x'])+","+str(next_cid.location['y'])+")")
        try:
            next_cid.click()
        except:
            time.sleep(2)
            print("clicking did not happen?")
            #driver.execute_script("window.scrollTo("+str(next_cid.location['x'])+","+str(next_cid.location['y'])+")")
            ActionChains(driver).move_to_element(next_cid).click().perform() #what happens if fail here? I don't know, currently the program terminates
            ## probably I have to add continue here

        time.sleep(1)
        # temp=driver.find_element_by_class_name(last_selection)
        # print(temp)
        # wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.ui-widget-content slick-row active even selected")))
        # if 'even' in last_selection:
        #     last_selection="ui-widget-content slick-row active odd selected"
        # else:
        #     last_selection="ui-widget-content slick-row active even selected"

        soup = BS(driver.page_source, features="html.parser")

        # #get cid number 
        # ## note that data-merged-defect id can be different
        # ## than what is shown as cid on webpage
        # try:
        #     cid=soup.find("div",{"class":["ui-widget-content slick-row active even selected","ui-widget-content slick-row active odd selected"]})
        #     cid=cid.find("div",{"class":"slick-cell l0 r0 cid selected"})
        #     cid=cid.find("div",{"class":"number"})
        #     cid=int(cid.text)
        # except:
        #     print("reading cid did not work")
        #     exit()
        #     continue

        #check if this alert id has been already handled
        temp = soup.find_all("tr", {"class": ["event-tree-node ng-scope","event-tree-node ng-scope selected"]})
        if len(temp)==0:
            print("logic error. no cid found in occurrence table ")
            continue
        temp=temp[0]
        try:
            defect_id=temp["data-merged-defect-id"].strip()
            defect_id=int(defect_id)
        except Exception as e:
            print("cannot find defect_id.",e)
            continue
        # if defect_id != cid: 
        #     print("this is the case where cid is diferent", defect_id, cid)
        #     defect_id=cid 
        with connection.cursor() as cursor:
            query="select idalerts from alerts where cid="+str(defect_id)+" and stream='"+str(project)+"';"
            cursor.execute(query)
            result=cursor.fetchone()
            if result is None:
                continue
            alert_id=result["idalerts"]
            query="select * from occurrences where alert_id="+str(alert_id)
            cursor.execute(query)
            result=cursor.fetchall()
        if len(result)>0:
            if defect_id not in unique_alerts:
                unique_alerts.append(defect_id)
            print("alert id already exists",defect_id,alert_id)
            print("current count of unique alerts: ",len(unique_alerts))
            if (len(unique_alerts) >= alerts_per_page):
                break #break this page
            continue
        else:
            if defect_id not in unique_alerts:
                unique_alerts.append(defect_id)
            print("new alert id found: ",defect_id,alert_id)
            print("current count of unique alerts: ",len(unique_alerts))

        ### Note that the code will only come up to this point if
        ### the defect id is updated

        occurrences = soup.find_all("div", {"class": "occurrences-data"})
        if len(occurrences) != 1:
            print("logic errorwith occurrences... exiting")
            exit()
        occurrences = occurrences[0] #there should be only one. And always there should be one.
        tables = occurrences.find_all("table")
        try:
            read_table(driver, tables, defect_id)
        except Exception as e:
            print("reading table did not work.", e)
        # if (defect_id == last_defect_id):
        #     print("page end reached",defect_id)
        #     #click on to next page and break this while loop
        #     next_page=driver.find_element_by_xpath('//*[@id="details-pager"]/div/span/span[5]')
        #     next_page.click()
        #     time.sleep(sleep_per_page)
        #     break
        # else:
        #     last_defect_id = defect_id
        if (len(unique_alerts) >= alerts_per_page):
            break
    next_page=driver.find_element_by_xpath('//*[@id="details-pager"]/div/span/span[5]')
    next_page.click()
    time.sleep(sleep_per_page)