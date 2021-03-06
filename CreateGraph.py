import py2neo
from py2neo import Graph, Node, Relationship
import pymysql

from DbConnection import connectToMySQL

import json

def connectToGraph():
    #Authenticate user
    py2neo.authenticate("localhost:7474", "neo4j", "neo4jDINU")

    #Connect to Graph
    graph = Graph("http://localhost:7474/db/data/", bolt = False)

    return graph

def createNodes(json, diagramType, graphType):
    print("Node Creation started")

    graph = connectToGraph()

    count = 0
    while count < len(json['nodeDataArray']):
        #Define Nodes

        if graphType == "Block":
            node = Node(diagramType, key=json['nodeDataArray'][count]['key'], text=json['nodeDataArray'][count]['text'])
        elif graphType == "LogicGate":
            if json['nodeDataArray'][count]['category'] == "input":
                node = Node(diagramType, key=json['nodeDataArray'][count]['key'], symbol=json['nodeDataArray'][count]['category'],
                                        text=json['nodeDataArray'][count]['text'])
            else:
                node = Node(diagramType, key=json['nodeDataArray'][count]['key'], symbol=json['nodeDataArray'][count]['category'])
        elif graphType == "Flowchart":
            if diagramType == "Teacher" and 'numberExpected' in json['nodeDataArray'][count] and 'stepMark' in json['nodeDataArray'][count]:
                node = Node(diagramType, key=json['nodeDataArray'][count]['key'],
                                         symbol=json['nodeDataArray'][count]['category'],
                                         text=json['nodeDataArray'][count]['text'],
                                         numberExpected=json['nodeDataArray'][count]['numberExpected'],
                                         stepMark=json['nodeDataArray'][count]['stepMark'])
            else:
                node = Node(diagramType, key=json['nodeDataArray'][count]['key'],
                                         symbol=json['nodeDataArray'][count]['category'],
                                         text=json['nodeDataArray'][count]['text'])        

        #Create node in graph
        graph.create(node)
        count += 1

    print("Node Creation finished")

def createRelationships(json, diagramType, graphType):
    print("Relationship Creation started")

    graph = connectToGraph()

    count = 0
    while count < len(json['linkDataArray']):

        fromNode = graph.find_one(diagramType, property_key='key', property_value=json['linkDataArray'][count]['from'])
        toNode = graph.find_one(diagramType, property_key='key', property_value=json['linkDataArray'][count]['to'])

        if graphType == "Flowchart" and 'text' in json['linkDataArray'][count]:
            relationship = Relationship(fromNode, json['linkDataArray'][count]['text'].upper(), toNode)
        else:
            relationship = Relationship(fromNode, toNode)
            
        graph.create(relationship)
        count += 1

    print("Relationship Creation finished")

def createNeo4jGraph(graphType, diagramType, diagramId):
    connection = connectToMySQL()
    cur = connection.cursor()

    if graphType == "Block" and diagramType == "Teacher":
        cur.execute("SELECT answerDiagram FROM process_question WHERE processqId = %s", (diagramId))
    elif graphType == "Block" and diagramType == "Student":
        cur.execute("SELECT answerDiagram FROM process_stud_answer WHERE processStudAnsId = %s", (diagramId))
    elif graphType == "LogicGate" and diagramType == "Teacher":
        cur.execute("SELECT answerDiagram FROM logic_gate_question WHERE logicgateqId = %s", (diagramId))
    elif graphType == "LogicGate" and diagramType == "Student":
        cur.execute("SELECT answerDiagram FROM logic_gate_stud_answer WHERE logicgateStudAnsId = %s", (diagramId))   
    elif graphType == "Flowchart" and diagramType == "Teacher":
        cur.execute("SELECT answerDiagram FROM flowchart_question WHERE flowchartqId = %s", (diagramId))
    elif graphType == "Flowchart" and diagramType == "Student":
        cur.execute("SELECT answerDiagram FROM flowchart_stud_answer WHERE flowchartStudAnsId = %s", (diagramId))    

    resultSet = cur.fetchone()
    cur.close()
    connection.close()

    jsonData = json.loads(resultSet[0])

    createNodes(jsonData, diagramType, graphType)
    createRelationships(jsonData, diagramType, graphType)    

def deleteStudentGraph():
    print("Student Graph Deletion started")

    graph = connectToGraph()
    graph.run("MATCH (n:Student) DETACH DELETE n")

    print("Student Graph Deletion finished")

def deleteAllAfterMarking():
    print("All Graph Deletion started")

    graph = connectToGraph()
    graph.run("MATCH (n) DETACH DELETE n")

    print("All Graph Deletion finished")



