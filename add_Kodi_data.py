import pymysql
import datetime
import requests
import json
import os
import time
import dateutil.parser

#Kodi project runs Coverity Scan only on master branch
#discussion on - https://forum.kodi.tv/showthread.php?tid=342142&pid=2835880#pid2835880

token=os.environ["githubtoken"] 

def is_number(n):
    try:
        int(n)
    except ValueError:
        return False
    return True

#mysql conncetion
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='890coverity',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def addBugType(bugType,impact,category):
    with connection.cursor() as cursor:
        try:
            query= 'insert into bug_types values (null,"'+bugType+'","'+impact+'","'+category+'");'
            cursor.execute(query)
        except Exception as e:
            print(e)
def typeId_ifexists(bugType):
    with connection.cursor() as cursor:
        query='select idbug_types from bug_types where type="'+bugType+'";'
        cursor.execute(query)
        result=cursor.fetchone()
        if result and 'idbug_types' in result.keys():
            return result['idbug_types']
        return None


def addFile(filename):
    #this function returns a boolean if there is a valid link for the file on master branch
    with connection.cursor() as cursor:
        github="https://github.com/xbmc/xbmc/tree/master"+filename
        r=requests.get(github)
        if r.status_code == 200:
            query='insert into files values(null,"Kodi","'+filename+'","'+github+'");'
            flag=True
        else:
            query='insert into files values(null,"Kodi","'+filename+'","invalid");'
            flag=False 
        try:
            cursor.execute(query)
        except Exception as e:
            print(e)
        return flag

def fileId_ifexists(filename):
    with connection.cursor() as cursor:
        query='select idfiles from files where filepath_on_coverity ="'+filename+'";'
        cursor.execute(query)
        result=cursor.fetchone()
        if result and 'idfiles' in result.keys():
            return result['idfiles']
        return None


def add_file_commits(filename,fileid):
    print(filename)
    header={"Authorization":"token "+token}
    url="https://api.github.com/repos/xbmc/xbmc/commits?path="+filename
    page=1
    commits=[]
    while True:
        #loop to handle pagination
        r=requests.get(url,params={'page':page,'sha':'master'},headers=header)
        while not r.ok:
            #handle api rate limit
            time.sleep(3)
            r=requests.get(url,params={'page':page,'sha':'master'},headers=header)
        data=json.loads(r.content)
        print(len(data),page)

        if(len(data))==0:
            #reached end of pagination
            break

        #read current data and increment page
        commits.extend(data)
        page+=1
    
    
    #add all commits in database
    for c in commits:
        author_date=(dateutil.parser.parse(c['commit']['author']['date'])).strftime('%y/%m/%d')
        commit_date=(dateutil.parser.parse(c['commit']['committer']['date'])).strftime('%y/%m/%d')
        query="insert into filecommits values(null,"+str(fileid)+",'"+str(c['sha'])+"','"+ \
                str(author_date) +"','"+str(commit_date)+"');"
        with connection.cursor() as cursor:
            try:
                cursor.execute(query)
            except Exception as e:
                print (e)




if __name__=="__main__":
    #open xml file
    import xml.etree.ElementTree as ET
    tree = ET.parse('AllKodi.xml')
    root = tree.getroot()

    for child in root:
        data=child.attrib

        #replace blank data with null
        for k in data.keys():
            if data[k]=="":
                data[k]="null"
        
        #handle bug_type
        if typeId_ifexists(data["type"])==None:
            addBugType(data["type"],data["impact"],data["category"])
        bugTypeId=typeId_ifexists(data["type"])

        #handle file
        valid_github_link=False
        if fileId_ifexists(data["file"])==None:
            valid_github_link = addFile(data["file"])
        fileId=fileId_ifexists(data["file"])

        #look for github commits only if there is a valid github link on the master branch
        if valid_github_link:
            filename=data["file"]
            #make api call and put commits into database
            add_file_commits(filename,fileId)
        


        
