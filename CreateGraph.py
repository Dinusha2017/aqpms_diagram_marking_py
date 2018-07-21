import py2neo
from py2neo import Graph, Node, Relationship
import pymysql

import json

mySQLhostname = 'localhost'
mySQLusername = 'root'
mySQLpassword = ''
mySQLdatabase = 'question_marking_system'

# print("NodeArray: ")
# print(json['nodeDataArray'])
# print("Text of first node: ")
# print(json['nodeDataArray'][0]['text'])
# print("length of nodeDataArray: " + str(len(json['nodeDataArray'])))
# print("linkDataArray: ")
# print(json['linkDataArray'])
# print("from of first relationship: ")
# print(json['linkDataArray'][0]['from'])

def connectToGraph():
    #Authenticate user
    # py2neo.authenticate("localhost:7474", "neo4j", "neo4j")

    #Connect to Graph
    # graph = Graph("http://localhost:7474/db/data/")
    graph = Graph("bolt://localhost:7474/db/data/", user="neo4j", password="neo4j")

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

        #Create node in graph
        graph.create(node)
        count += 1

    print("Node Creation finished")

def createRelationships(json, diagramType):
    print("Relationship Creation started")

    graph = connectToGraph()

    count = 0
    while count < len(json['linkDataArray']):

        fromNode = graph.find_one(diagramType, property_key='key', property_value=json['linkDataArray'][count]['from'])
        toNode = graph.find_one(diagramType, property_key='key', property_value=json['linkDataArray'][count]['to'])

        relationship = Relationship(fromNode, toNode)
        graph.create(relationship)
        count += 1

    print("Relationship Creation finished")

def createNeo4jGraph(graphType, diagramType, diagramId):
    connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)
    cur = connection.cursor()

    if graphType == "Block" and diagramType == "Teacher":
        cur.execute("SELECT answerDiagram FROM process_question WHERE processqId = %s", (diagramId))
    elif graphType == "Block" and diagramType == "Student":
        cur.execute("SELECT answerDiagram FROM process_stud_answer WHERE processStudAnsId = %s", (diagramId))
    elif graphType == "LogicGate" and diagramType == "Teacher":
        cur.execute("SELECT answerDiagram FROM logic_gate_question WHERE logicgateqId = %s", (diagramId))
    elif graphType == "LogicGate" and diagramType == "Student":
        cur.execute("SELECT answerDiagram FROM logic_gate_stud_answer WHERE logicgateStudAnsId = %s", (diagramId))   

    resultSet = cur.fetchone()
    print(resultSet)
    cur.close()
    connection.close()

    jsonData = json.loads(resultSet[0])

    createNodes(jsonData, diagramType, graphType)
    createRelationships(jsonData, diagramType)    

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

# def createBDDNode(key, inputLbl):
#     graph = connectToGraph()
#     node = Node("TBDD", key=key, inputLabel=inputLbl)
#     graph.create(node)

# def createBDDRelationship(fromKey, toKey, relationLbl):
#     graph = connectToGraph()
#     fromNode = graph.find_one("TBDD", property_key='key', property_value=fromKey)
#     toNode = graph.find_one("TBDD", property_key='key', property_value=toKey)
#     relationship = Relationship(fromNode, relationLbl, toNode)
#     graph.create(relationship)    



