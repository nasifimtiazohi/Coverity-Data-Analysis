import pymysql

connection = pymysql.connect(host='localhost',
                             user='root',
                             db='890coverity',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

queries=[
    "insert into projects values(null,'Kodi','https://github.com/xbmc/xbmc','git://github.com/xbmc/xbmc.git','2012-08-28','2019-03-16');"
]

with connection.cursor() as cursor:
    cursor.execute(queries[-1])