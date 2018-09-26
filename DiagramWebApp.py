from flask import Flask, jsonify

import os
import shutil

from DbConnection import connectToMySQL

from BlockDiagramMatching import markStudDFSBlockAnswer
from CreateGraph import createNeo4jGraph, deleteStudentGraph, deleteAllAfterMarking

from LogicGateMatching import markLogicGateAnswer
from LogicGateSimulation import simulateLogicGate, deleteSimulationCombinationData

from FlowchartMatching import markFlowchartAnswer

import pymysql

webapp = Flask(__name__)

def markDiagram(question_Id, graphType):
    print("QuestionId: " + question_Id)

    directory = "StudentAnswerProgram"

    try:
        print("Inside try")

        createNeo4jGraph(graphType, "Teacher", question_Id)

        isExactMatch = ""
        noOfInputs = 0

        if graphType == "LogicGate":
            connection = connectToMySQL()
            cur = connection.cursor()
            cur.execute("SELECT isExactMatch, noOfInputs FROM logic_gate_question WHERE logicgateqId = %s", (question_Id))
            resultSet = cur.fetchone()
            cur.close()
            connection.close()

            isExactMatch = resultSet[0]
            noOfInputs = resultSet[1]

            if isExactMatch == "false":
                simulateLogicGate("Teacher", noOfInputs, question_Id)
        elif graphType == "Flowchart":
            if not os.path.exists(directory):
                os.makedirs(directory)
            os.chdir(directory)    

        connection = connectToMySQL()
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
            elif graphType == "Flowchart":
                markFlowchartAnswer(question_Id, row[0])        

            deleteStudentGraph()

        deleteAllAfterMarking()
        if graphType == "LogicGate" and isExactMatch == "false":
            deleteSimulationCombinationData()
        elif graphType == "Flowchart":
            os.chdir('..')

            if os.path.isdir(directory):
                shutil.rmtree(directory)
    except Exception as e:
        deleteAllAfterMarking()
        if graphType == "LogicGate":  #  and isExactMatch == "false"
            deleteSimulationCombinationData()
        elif graphType == "Flowchart":
            os.chdir('..')

            if os.path.isdir(directory):
                shutil.rmtree(directory)

        print('Exception: ')
        print(e)    

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

@webapp.route("/flowchart/question/<question_Id>", methods=['GET'])
def markFlowchartQuestion(question_Id):    
    return markDiagram(question_Id, "Flowchart")    

if __name__ == '__main__':
    webapp.run(host = '142.93.208.98', port = 5000, debug = True)  #   127.0.0.1