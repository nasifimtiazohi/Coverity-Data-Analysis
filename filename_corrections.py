import pymysql 
import sys

#read the project name
project=str(sys.argv[1])

#open sql connection 
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results=cursor.fetchall()
    return results

query="select * from files where project='"+project+"';"

results=execute(query)

i=0
# for item in results:
#     temp=item['filepath_on_coverity']
#     cut='/home/jenkins/workspace/LINUX-64-CoverityScan'
#     if cut in temp:
#         temp=temp[45:]
#         fid=str(item['idfiles'])
#         query='update files set filepath_on_coverity="'+temp+'" where idfiles='+fid
#         execute(query)
#         i+=1
# print(i)
temp=[]
for item in results:
    t=item['filepath_on_coverity']
    t=t.split("/")
    t=t[1]
    if t not in temp:
        temp.append(t)
print(temp)

    