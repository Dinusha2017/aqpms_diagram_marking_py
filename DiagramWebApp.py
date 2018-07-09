from flask import Flask, jsonify

from BlockDiagramMatching import createBlockGraph, markStudDFSBlockAnswer
from CreateGraph import deleteStudentGraph, deleteAllAfterMarking

import pymysql

mySQLhostname = 'localhost'
mySQLusername = 'root'
mySQLpassword = ''
mySQLdatabase = 'question_marking_system'

webapp = Flask(__name__)

@webapp.route("/")
def hello():
    return "Hello World!"

@webapp.route("/block/questionPaper/<questionPaper_Id>/question/<question_Id>", methods=['GET'])
def markBlockQuestion(questionPaper_Id, question_Id):

    print("QuestionPaperId: " + questionPaper_Id)
    print("QuestionId: " + question_Id)

    try:
        print("Inside try")

        createBlockGraph("Teacher", question_Id)

        connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)
        cur = connection.cursor()
        cur.execute("SELECT studAnswerId FROM student_answer WHERE questionPaperId = %s and questionId = %s and markedStatus = %s", 
                    (questionPaper_Id, question_Id, "false"))
        resultSet = cur.fetchall()
        print(resultSet)
        cur.close()
        connection.close()

        for row in resultSet:
            print(row[0])

            createBlockGraph("Student", row[0])
            markStudDFSBlockAnswer(question_Id, row[0])

            deleteStudentGraph()

        deleteAllAfterMarking()
    except:
        deleteAllAfterMarking()
        return jsonify({"status":"failed"})

    return jsonify({"status":"successful"})

if __name__ == '__main__':
    webapp.run(debug=True)