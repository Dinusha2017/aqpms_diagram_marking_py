import py2neo
from py2neo import Graph, Node, Relationship

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
    py2neo.authenticate("localhost:7474", "neo4j", "neo4jDINU")

    #Connect to Graph
    graph = Graph("http://localhost:7474/db/data/")

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



