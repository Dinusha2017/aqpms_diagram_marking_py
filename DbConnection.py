import pymysql

mySQLhostname = 'localhost'
mySQLusername = 'root'
mySQLpassword = ''
mySQLdatabase = 'question_marking_system'

def connectToMySQL():
    return pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)