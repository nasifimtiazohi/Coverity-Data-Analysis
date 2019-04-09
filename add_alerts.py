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
datafile=sys.argv[2]

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
        if fileId_ifexists(data["file"])==None:
            addFile(data["file"])
        fileId=fileId_ifexists(data["file"])

        
        
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
        


        
