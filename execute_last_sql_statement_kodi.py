import pymysql

connection = pymysql.connect(host='localhost',
                             user='root',
                             db='890coverity',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

queries=[
    #initiate Kodi on project database
    "insert into projects values(null,'Kodi','https://github.com/xbmc/xbmc','git://github.com/xbmc/xbmc.git','2012-08-28','2019-03-16','master');",
    #invalidate the alerts before first detected
    "update alerts \
    set is_invalid=1 \
    where first_detected  < \
                            (select start_date \
                            from projects \
                            where stream='Kodi')",
    "insert into projects values(null,'ovirt-engine','git://github.com/oVirt/ovirt-engine','https://github.com/oVirt/ovirt-engine','2013-06-24','2019-03-18','master');"
]

with connection.cursor() as cursor:
    for q in queries:
        cursor.execute(q)