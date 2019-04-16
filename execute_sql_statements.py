import pymysql
import sys 

connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

queries=[
    #initiate Kodi on project database
    "insert into projects values(null,'Kodi','git://github.com/xbmc/xbmc.git','https://github.com/xbmc/xbmc',1,'master','2012-08-28','2019-03-19');",
    #invalidate the alerts before first detected
    "update alerts \
    set is_invalid=1 \
    where stream='Kodi' and first_detected  < \
                            (select start_date \
                            from projects \
                            where name='Kodi')",
    "insert into projects values(null,'ovirt-engine','git://github.com/oVirt/ovirt-engine','https://github.com/oVirt/ovirt-engine',1,'master','2013-06-24','2019-03-18');",
    "update alerts \
    set is_invalid=1 \
    where stream='ovirt-engine' and first_detected  < \
                            (select start_date \
                            from projects \
                            where name='ovirt-engine')",
    "insert into projects values(null,'Firefox','https://hg.mozilla.org/mozilla-central','https://github.com/mozilla/gecko-dev',1,'master', '2006-02-22','2018-10-26');",
    "update alerts \
    set is_invalid=1 \
    where stream='Firefox' and first_detected  < \
                            (select start_date \
                            from projects \
                            where name='Firefox')",
    '''update alerts
        set is_invalid=2
        where stream='Firefox'
        and bug_type=53
        and first_detected = '2015-03-05'
        and last_snapshot_id=157442;''',
    "insert into projects values(null,'Linux','http://git.kernel.org/','https://github.com/torvalds/linux',1,'master','2012-05-17','2019-04-08');",
    "update alerts \
    set is_invalid=1 \
    where stream='Linux' and first_detected  < \
                            (select start_date \
                            from projects \
                            where name='Linux')",
    '''update alerts
        set is_invalid=2
        where stream='Linux'
        and bug_type=24
        and first_detected = '2016-11-06'
        and last_snapshot_id=166244;'''
    
]

with connection.cursor() as cursor:
    for q in queries:
        try:
            cursor.execute(q)
        except Exception as e:
            print (e)