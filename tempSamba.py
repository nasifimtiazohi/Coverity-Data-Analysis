'''pain in the ass work for transferring samba
data from old database because coverity scan is down'''
import pymysql
import datetime
import requests
import json
import os
import time
import dateutil.parser
import sys
import pandas as pd

#read system arguments
project_name=sys.argv[1]

def is_number(n):
    try:
        int(n)
    except ValueError:
        return False
    return True

#mysql conncetion
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
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
    with connection.cursor() as cursor:
        query = "insert into files values(null,'"+str(project_name)+"','"+str(filename)+"');"
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






if __name__=="__main__":
    query='''select * from coverity.alerts a
            join coverity.bug_types b
            on a.bug_type=b.idbug_types
            where a.stream='Samba' order by cid desc;'''
    df=pd.read_sql(query,connection)
    datalist=[]
    for row in df.itertuples():
        d={}
        for k in df.keys():
            d[k]=row[df.columns.get_loc(k)+1]
        datalist.append(d)
    errors=open("errors.txt","w")


    for data in datalist:
        #replace blank data with nullc
        for k in data.keys():
            if data[k]=="" or data[k]==None or str(data[k])=="NaT" or str(data[k])=="nan":
                data[k]="null"
        
        if is_number(data['cwe']):
            data['cwe']=int(data['cwe'])

        
        #handle bug_type
        if typeId_ifexists(data["type"])==None:
            addBugType(data["type"],data["impact"],data["category"])
        bugTypeId=typeId_ifexists(data["type"])

        #handle file
        if fileId_ifexists(data["file"])==None:
            addFile(data["file"])
        fileId=fileId_ifexists(data["file"])

        
        
        #add alerts
        
        arguments=[
            data["cid"], 
            project_name,
            str(bugTypeId), 
            data["status"] ,
            data["firstDetected"].strftime('%y-%m-%d'),
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
        # add an escaping string function. not the best practice. but easiest fix.
        for a in arguments:
            if type(a)==str:
                a=connection.escape_string(a)
        query="insert into alerts values (null,"
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
        


        
