'''this file contains code
on how I corrected filename prefixes 
for each projects'''
import pymysql 
import sys

#read the project name
project=str(sys.argv[1])

#open sql connection 
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='soverityscan_sandbox',
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

temp=[]
a=[]
for item in results:
    full=item['filepath_on_coverity']
    t=full.split("/")
    if t[1] not in temp:
        temp.append(t[1])
    if t[1]=='base':
        print(full)

print(temp)

#CORRECTION FOR SAMBA
i=0
for item in results:
    temp=item['filepath_on_coverity']
    cut='/samba'
    if temp.startswith(cut):
        temp=temp[6:]
        fid=str(item['idfiles'])
        query='update files set filepath_on_coverity="'+temp+'" where idfiles='+fid
        execute(query)
        i+=1
print(i)
i=0
for item in results:
    temp=item['filepath_on_coverity']
    cut='/bin/default'
    if temp.startswith(cut):
        temp=temp[12:]
        fid=str(item['idfiles'])
        query='update files set filepath_on_coverity="'+temp+'" where idfiles='+fid
        execute(query)
        i+=1
print(i)
i=0
for item in results:
    temp=item['filepath_on_coverity']
    cut='/base/src'
    if temp.startswith(cut):
        temp=temp[9:]
        fid=str(item['idfiles'])
        query='update files set filepath_on_coverity="'+temp+'" where idfiles='+fid
        execute(query)
        i+=1
print(i)

#CORRECTION FOR KODI
# i=0
# for item in results:
#     temp=item['filepath_on_coverity']
#     cut='/home/jenkins/workspace/LINUX-64-soverityscan_sandbox'
#     if cut in temp:
#         temp=temp[45:]
#         fid=str(item['idfiles'])
#         query='update files set filepath_on_coverity="'+temp+'" where idfiles='+fid
#         execute(query)
#         i+=1
# print(i)


#CORRECTIONS FOR LINUX
# i=0
# for item in results:
#     temp=str(item['filepath_on_coverity'])
#     cut='/linux'
#     if temp.startswith(cut):
#         temp=temp[6:]
#         fid=str(item['idfiles'])
#         query='update files set filepath_on_coverity="'+temp+'" where idfiles='+fid
#         execute(query)
#         i+=1
# print(i)


#CORRECTIONS FOR FIREFOX
# i=0
# for item in results:
#     temp=str(item['filepath_on_coverity'])
#     cut='/mozilla'
#     if temp.startswith(cut):
#         temp=temp[8:]
#         fid=str(item['idfiles'])
#         query='update files set filepath_on_coverity="'+temp+'" where idfiles='+fid
#         execute(query)
#         i+=1
# print(i)

# i=0
# for item in results:
#     temp=str(item['filepath_on_coverity'])
#     cut='/base/src/mozilla'
#     if temp.startswith(cut):
#         temp=temp[17:]
#         fid=str(item['idfiles'])
#         query='update files set filepath_on_coverity="'+temp+'" where idfiles='+fid
#         execute(query)
#         i+=1
# print(i)   