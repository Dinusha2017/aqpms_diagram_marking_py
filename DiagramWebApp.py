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

def markDiagram(question_Id, graphType, caller):
    print("QuestionId: " + question_Id)

    directory = "StudentAnswerProgram"

    try:
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
        cur.close()
        connection.close()

        for row in resultSet:
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

        if caller == "PaperMarker":
            return "false"    

        return jsonify({"status":"failed"})

    if caller == "PaperMarker":
        return "true"

    return jsonify({"status":"successful"})

@webapp.route("/")
def hello():
    return "Hello World!"

@webapp.route("/block/question/<question_Id>", methods=['GET'])
def markBlockQuestion(question_Id):
    return markDiagram(question_Id, "Block", "BlockMarker")

@webapp.route("/logicgate/question/<question_Id>", methods=['GET'])
def markLogicGateQuestion(question_Id):    
    return markDiagram(question_Id, "LogicGate", "LogicGateMarker")

@webapp.route("/flowchart/question/<question_Id>", methods=['GET'])
def markFlowchartQuestion(question_Id):    
    return markDiagram(question_Id, "Flowchart", "FlowchartMarker")    

@webapp.route("/questionPaper/<question_paper_Id>", methods=['GET'])
def markQuestionPaper(question_paper_Id):    
    connection = connectToMySQL()
    cur = connection.cursor()
    cur.execute("SELECT questionId, type FROM question WHERE questionPaperId = %s AND " + 
                "(type='Block' OR type='LogicGate' OR type='Flowchart')", 
                (question_paper_Id))
    resultSet = cur.fetchall()
    cur.close()
    connection.close()

    for row in resultSet:
        questionId = str(row[0])
        questionType = row[1]

        status = markDiagram(questionId, questionType, "PaperMarker")

        if status == "false":
            return jsonify({"status":"failed"})        

    return jsonify({"status":"successful"})     

if __name__ == '__main__':
    webapp.run(host = '127.0.0.1', port = 5000, debug = True)  #     142.93.208.98