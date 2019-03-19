import pymysql
import datetime
#mysql conncetion
def is_number(n):
    try:
        int(n)
    except ValueError:
        return False
    return True
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='890coverity',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)
import xml.etree.ElementTree as ET
tree = ET.parse('KodiProject.xml')
root = tree.getroot()

errors=open("errors.txt","w")

for child in root:
    data=child.attrib
    
    for k in data.keys():
        if data[k]=="":
            data[k]="null"
    # lastTriaged=data["lastTriaged"]
    # print(lastTriaged)
    # if lastTriaged!="null":
    #     datetime.datetime.strptime(data["firstDetected"],'%m/%d/%y %H:%M').strftime('%y/%m/%d %H:%M')
    arguments=[
        data["snapshotId"],
        data["streamName"],
        data["snapshotDate"],
        data["snapshotDescription"],
        data["totalDetectedDefectCount"],
        data["newlyDetectedDefectCount"],
        data["newlyEliminatedDefectCount"],
        data["analysisTime"],
        data["linesOfCodeCount"],
        data["CodeVersionDate"],
        data["fileCount"],
        data["functionCount"],
        data["snapshotVersion"],
        data["blankLinesCount"],
        data["buildTime"],
        data["commentLinesCount"],
        data["HasAnalysisSummaries"],
        data["snapshotTarget"]
    ]
    query="insert into snapshots values ("
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