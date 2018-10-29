import pymysql

mySQLhostname = '104.248.239.53'  # localhost
mySQLusername = 'aqpmsuser'  # root
mySQLpassword = 'aqpms'
mySQLdatabase = 'question_marking_system'

def connectToMySQL():
    return pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)