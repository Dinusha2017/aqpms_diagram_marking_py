import pymysql

mySQLhostname = '178.128.158.92'  # localhost
mySQLusername = 'aqpmsuser'  # root
mySQLpassword = 'aqpms'
mySQLdatabase = 'question_marking_system'

def connectToMySQL():
    return pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)