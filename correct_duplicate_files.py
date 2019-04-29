'''after correcting for filenames,
ther would be duplicate files in the files table,
correct them, keep the "proper" (see logic) one '''
import pymysql
import sys

project=sys.argv[1]

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

query='''select filepath_on_coverity, count(*)
        from files 
        where project = "'''+project+'''"
        group by filepath_on_coverity
        having count(*) > 1'''
results=execute(query)

for item in results:
    filepath=item['filepath_on_coverity']
    query='''select idfiles 
        from files
        where filepath_on_coverity="'''+filepath+'''"
        order by idfiles asc;'''
    temp=execute(query)
    ids=[]
    for t in temp:
        ids.append(t['idfiles'])
    
    max=-1
    main_id=-1
    for id in ids:
        query="select count(*) as c from filecommits where file_id="+str(id)
        c=execute(query)[0]['c']
        if c>max:
            max=c
            main_id=id
    
    
    ids.remove(main_id)

    for replace_id in ids:
        print(replace_id)
        #update alerts
        query="update alerts set file_id="+str(main_id)+" where file_id="+str(replace_id)
        execute(query)

        #update occurrences
        query="update occurrences set file_id="+str(main_id)+" where file_id="+str(replace_id)
        execute(query)

        #delete from files
        query="delete from files where idfiles="+str(replace_id)
        execute(query)

