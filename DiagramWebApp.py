from flask import Flask, jsonify

from BlockDiagramMatching import markStudDFSBlockAnswer
from CreateGraph import createNeo4jGraph, deleteStudentGraph, deleteAllAfterMarking

from LogicGateMatching import markLogicGateAnswer
from LogicGateSimulation import simulateLogicGate, deleteSimulationCombinationData

import pymysql

mySQLhostname = 'localhost'
mySQLusername = 'root'
mySQLpassword = ''
mySQLdatabase = 'question_marking_system'

webapp = Flask(__name__)

def markDiagram(question_Id, graphType):
    print("QuestionId: " + question_Id)

    try:
        print("Inside try")

        createNeo4jGraph(graphType, "Teacher", question_Id)

        isExactMatch = ""
        noOfInputs = 0

        if graphType == "LogicGate":
            connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)
            cur = connection.cursor()
            cur.execute("SELECT isExactMatch, noOfInputs FROM logic_gate_question WHERE logicgateqId = %s" % (1))
            resultSet = cur.fetchone()
            cur.close()
            connection.close()

            isExactMatch = resultSet[0]
            noOfInputs = resultSet[1]

            if isExactMatch == "false":
                simulateLogicGate("Teacher", noOfInputs, question_Id)

        connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)
        cur = connection.cursor()
        cur.execute("SELECT studAnswerId FROM student_answer WHERE questionId = %s and markedStatus = %s", 
                    (question_Id, "false"))
        resultSet = cur.fetchall()
        print(resultSet)
        cur.close()
        connection.close()

        for row in resultSet:
            print(row[0])

            createNeo4jGraph(graphType, "Student", row[0])

            if graphType == "Block":
                markStudDFSBlockAnswer(question_Id, row[0])
            elif graphType == "LogicGate":
                markLogicGateAnswer(question_Id, row[0], isExactMatch, noOfInputs)    

            deleteStudentGraph()

        deleteAllAfterMarking()
        if graphType == "LogicGate" and isExactMatch == "false":
            deleteSimulationCombinationData()
    except:
        deleteAllAfterMarking()
        if graphType == "LogicGate" and isExactMatch == "false":
            deleteSimulationCombinationData()

        return jsonify({"status":"failed"})

    return jsonify({"status":"successful"})

@webapp.route("/")
def hello():
    return "Hello World!"

@webapp.route("/block/question/<question_Id>", methods=['GET'])
def markBlockQuestion(question_Id):
    return markDiagram(question_Id, "Block")

@webapp.route("/logicgate/question/<question_Id>", methods=['GET'])
def markLogicGateQuestion(question_Id):    
    return markDiagram(question_Id, "LogicGate")

if __name__ == '__main__':
    webapp.run(host = '138.197.211.217', port = 5000, debug = True)