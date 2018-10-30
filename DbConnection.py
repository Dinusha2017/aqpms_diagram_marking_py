import pymysql

mySQLhostname = '68.183.116.125'  # localhost
mySQLusername = 'aqpmsuser'  # root
mySQLpassword = 'aqpms'
mySQLdatabase = 'question_marking_system'

def connectToMySQL():
    return pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)