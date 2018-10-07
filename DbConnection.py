import pymysql

mySQLhostname = '104.248.116.101'  # localhost
mySQLusername = 'aqpmsuser'  # root
mySQLpassword = 'aqpms'
mySQLdatabase = 'question_marking_system'

def connectToMySQL():
    return pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)