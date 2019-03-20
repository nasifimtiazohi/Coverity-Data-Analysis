import pymysql
import datetime
import requests
import json
import os
import time
import dateutil.parser
import sys

#read system arguments
project_name=sys.argv[1]
github_repo=sys.argv[2]
datafile=sys.argv[3]

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
        github="https://github.com/"+github_repo + "/tree/master"+filename
        r=requests.get(github)
        if r.status_code == 200:
            query='insert into files values(null,"'+ project_name+'","'+filename+'","'+github+'");'
            flag=True
        else:
            query='insert into files values(null,"'+ project_name+'","'+filename+'","invalid");'
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
    url="https://api.github.com/repos/"+github_repo+"/commits?path="+filename
    page=1
    commits=[]
    while True:
        #loop to handle pagination
        r=requests.get(url,params={'page':page,'sha':'master'},headers=header)
        while not r.ok:
            #handle api rate limit
            print(r.content)
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
    tree = ET.parse(datafile)
    root = tree.getroot()

    errors=open("errors.txt","w")

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
        #it also controls for the case that filecommits will only be searched for at the
        #first time the file is added
        if valid_github_link:
            filename=data["file"]
            #make api call and put commits into database
            add_file_commits(filename,fileId)
        
        #add alerts
        arguments=[
            data["cid"], 
            project_name,
            str(bugTypeId), 
            data["status"] ,
            datetime.datetime.strptime(data["firstDetected"],'%m/%d/%y').strftime('%y/%m/%d'),
            data["owner"],
            data["classification"],
            data["severity"],
            data["action"],
            data["displayComponent"],
            str(fileId),
            data["function"],
            data["checker"],
            data["occurrenceCount"],
            data["cwe"],
            data["externalReference"],
            data["FirstSnapshot"],
            data["functionMergeName"],
            data["issueKind"],
            data["Language"],
            data["lastDetectedSnapshot"],
            data["lastTriaged"],
            data["legacy"],
            data["mergeExtra"],
            data["mergeKey"],
            data["ownerName"],
            0
        ]
        query="insert into alerts values ("
        for idx, arg in enumerate(arguments):

            #value cleaning
            arg=str(arg) #if not string
            arg=arg.strip() #if any whitespace ahead or trailing
            #remove illegal character
            arg=arg.replace('"',"'")



            if is_number(arg) or arg=="null":
                query+=arg
            else:
                query+='"'+arg+'"'
            if idx<len(arguments)-1:
                query+=","
        query+=");"
        with connection.cursor() as cursor:
            try:
                cursor.execute(query)
            except Exception as e:
                print(e,query)
                errors.write(str(e)+"\n")
        


        
