import pymysql

mySQLhostname = 'localhost'  #  68.183.116.125
mySQLusername = 'root'  #  aqpmsuser
mySQLpassword = ''  #aqpms
mySQLdatabase = 'research_new'

def connectToMySQL():
    return pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)