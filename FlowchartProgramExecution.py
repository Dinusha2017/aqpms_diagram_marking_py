import os
import sys
import subprocess

from CreateGraph import createNeo4jGraph, connectToGraph
from DbConnection import connectToMySQL

import re

from io import StringIO

import string
import random


def indentLine(indent, studentAnswerFile):
    indentCount = 0
    while indentCount < indent:
        studentAnswerFile.write("   ")
        indentCount = indentCount + 1


def indentNestedWhileAppendString(indent, line):
    indentCount = 0
    while indentCount < indent:
        line = line + "   "
        indentCount = indentCount + 1
    return line

def ifHasOnlyOnePath(caller,
                     graph,
                     stack,
                     stackAppendNode,
                     traversedNodes,
                     traversedCommonNodesAppendNode,
                     commonNodes,
                     currentNode,
                     ifNodes,
                     ifDictionary):
    stack.append(stackAppendNode)

    traversedNodes.append(traversedCommonNodesAppendNode)

    commonNodes.append(traversedCommonNodesAppendNode)

    if not currentNode in ifNodes:
        ifNodes.append(currentNode)

    commonNodePaths = graph.data("MATCH paths = (currentDecision:" + caller + ")-[*]->(commonNode:" + caller + ") WHERE " +
                                 "currentDecision.key={currentNodeKey} and commonNode.key={commonNodeKey} " +
                                 "RETURN count(paths)", parameters={"currentNodeKey": currentNode,
                                                                    "commonNodeKey": traversedCommonNodesAppendNode})

    commonNodeLoopPaths = graph.data("MATCH paths = (currentDecision:" + caller + ")-[*]->(commonNode:" + caller + ")-[*]->(commonNode:" + caller + ") WHERE " +
                                     "currentDecision.key={currentNodeKey} and commonNode.key={commonNodeKey} RETURN count(paths)",
                                     parameters={"currentNodeKey": currentNode, "commonNodeKey": traversedCommonNodesAppendNode})

    noOfPathsToCommonNode = commonNodePaths[0]['count(paths)'] - commonNodeLoopPaths[0]['count(paths)']
    if not currentNode in ifDictionary:
        ifDictionary[currentNode] = noOfPathsToCommonNode


def handleWhileTypeConversions(caller,
                               stack,
                               whileNextNode,
                               traversedNodes,
                               currentNode,
                               indent,
                               unindentWhile,
                               whileOrNot,
                               currentText,
                               whileTypeNodes,
                               visitedNodes):
    line = ""

    stack.append(whileNextNode)

    if traversedNodes.count(currentNode) == 1:
        randomGeneratedVarForTimeout = ''.join(random.choice(string.ascii_letters) for m in range(5))
        # set while loop timeout for 4 minutes from this point
        # line = line + randomGeneratedVarForTimeout + " = time.time() + 60*4" + "\n"
        line = line + randomGeneratedVarForTimeout + " = 0" + "\n"
        if indent > 0:
            line = indentNestedWhileAppendString(indent, line)
        line = line + whileOrNot + currentText.replace("?", "") + ":" + "\n"
        if indent > 0:
            line = indentNestedWhileAppendString(indent, line)
        line = line + "   " + randomGeneratedVarForTimeout + " = " + randomGeneratedVarForTimeout + " + 1\n"
        if indent > 0:
            line = indentNestedWhileAppendString(indent, line)
        # line = line + "   if time.time() > " + randomGeneratedVarForTimeout + ":\n"
        line = line + "   if " + randomGeneratedVarForTimeout + " >= 25:\n"
        if indent > 0:
            line = indentNestedWhileAppendString(indent, line)
        line = line + "      sys.exit(1)"

        whileTypeNodes.append(currentNode)
    elif traversedNodes.count(currentNode) > 1:
        lastWhileNodeKey = whileTypeNodes.pop()

        if currentNode == lastWhileNodeKey:
            indent = indent - 1
            unindentWhile = "true"

            visitedNodes.append(currentNode)

            if caller == "DoWhile":
                if traversedNodes.count(currentNode) == 2:
                    # remove to support the conditions coded for nested loops
                    traversedNodes = list(filter(lambda val: val != currentNode, traversedNodes))
        else:
            whileTypeNodes.append(lastWhileNodeKey)

    return line, indent, unindentWhile, traversedNodes


def handleWhileTraversal(loopPath,
                         traversedNodes,
                         currentNode,
                         yesCurrentChildNode,
                         noCurrentChildNode):
    currentStructure = "While"

    if loopPath[0]['TYPE(r)'] == "YES":
        whileOrNot = "while "
        if traversedNodes.count(currentNode) == 1:
            whileNextNode = yesCurrentChildNode[0]['child']['key']
        elif traversedNodes.count(currentNode) > 1:
            whileNextNode = noCurrentChildNode[0]['child']['key']
    elif loopPath[0]['TYPE(r)'] == "NO":
        whileOrNot = "while not "
        if traversedNodes.count(currentNode) == 1:
            whileNextNode = noCurrentChildNode[0]['child']['key']
        elif traversedNodes.count(currentNode) > 1:
            whileNextNode = yesCurrentChildNode[0]['child']['key']

    return whileOrNot, whileNextNode, currentStructure


def handleIfTypeConversions(graph,
                            stack,
                            currentNode,
                            traversedNodes,
                            noChildParents,
                            yesChildParents,
                            noCurrentChildNode,
                            yesCurrentChildNode,
                            currentText,
                            commonNodes,
                            ifNodes,
                            ifDictionary,
                            visitedNodes,
                            mainIfCompletedNoOfPaths):
    ifFound = "false"

    currentCommonNode = graph.data(
        "MATCH path1 = (currentDecision:Student)-[:YES]->(a:Student)-[*]->(commonNode:Student), "
        "path2 = (currentDecision:Student)-[:NO]->(b:Student)-[*]->(commonNode:Student)" +
        "WHERE currentDecision.key={currentNodeKey} and path1 <> path2 RETURN DISTINCT commonNode",
        parameters={"currentNodeKey": currentNode})

    if len(noChildParents) > 1 and traversedNodes.count(currentNode) == 1:
        if not currentCommonNode:
            currentCommonNode = graph.data(
                "MATCH path1 = (currentDecision:Student)-[:YES]->(a:Student)-[*]->(commonNode:Student), "
                "path2 = (currentDecision:Student)-[:NO]->(commonNode:Student)" +
                "WHERE currentDecision.key={currentNodeKey} and path1 <> path2 RETURN DISTINCT commonNode",
                parameters={"currentNodeKey": currentNode})

        if noCurrentChildNode[0]['child']['key'] == currentCommonNode[0]['commonNode']['key']:
            ifFound = "true"

            currentStructure = "If"

            line = "if " + currentText.replace("?", "") + ":"

            ifHasOnlyOnePath('Student', graph, stack, yesCurrentChildNode[0]['child']['key'], traversedNodes,
                             noCurrentChildNode[0]['child']['key'], commonNodes, currentNode, ifNodes,
                             ifDictionary)
    elif len(yesChildParents) > 1 and traversedNodes.count(currentNode) == 1:
        if not currentCommonNode:
            currentCommonNode = graph.data(
                "MATCH path1 = (currentDecision:Student)-[:YES]->(commonNode:Student), "
                "path2 = (currentDecision:Student)-[:NO]->(b:Student)-[*]->(commonNode:Student)" +
                "WHERE currentDecision.key={currentNodeKey} and path1 <> path2 RETURN DISTINCT commonNode",
                parameters={"currentNodeKey": currentNode})

        if yesCurrentChildNode[0]['child']['key'] == currentCommonNode[0]['commonNode']['key']:
            ifFound = "true"

            currentStructure = "IfNot"

            line = "if not " + currentText.replace("?", "") + ":"

            ifHasOnlyOnePath('Student', graph, stack, noCurrentChildNode[0]['child']['key'], traversedNodes,
                             yesCurrentChildNode[0]['child']['key'], commonNodes, currentNode, ifNodes,
                             ifDictionary)

    if ifFound == "false":
        if noCurrentChildNode[0]['child']['symbol'] == "Decision" and \
                not yesCurrentChildNode[0]['child']['symbol'] == "Decision":
            currentStructure = "IfElseIf"
        else:
            currentStructure = "IfElse"

        if not currentNode in ifNodes:
            commonNodes.append(currentCommonNode[0]['commonNode']['key'])
            ifNodes.append(currentNode)

        commonNodePaths = graph.data("MATCH paths = (currentDecision:Student)-[*]->(commonNode:Student) WHERE " +
                                           "currentDecision.key={currentNodeKey} and commonNode.key={commonNodeKey} " +
                                           "RETURN count(paths)", parameters={"currentNodeKey": currentNode,
                                                        "commonNodeKey": currentCommonNode[0]['commonNode']['key']})

        commonNodeLoopPaths = graph.data("MATCH paths = (currentDecision:Student)-[*]->(commonNode:Student)-[*]->(commonNode:Student) WHERE " +
                                     "currentDecision.key={currentNodeKey} and commonNode.key={commonNodeKey} RETURN count(paths)",
                                     parameters={"currentNodeKey": currentNode, "commonNodeKey": currentCommonNode[0]['commonNode']['key']})

        noOfPathsToCommonNode = commonNodePaths[0]['count(paths)'] - commonNodeLoopPaths[0]['count(paths)']

        if yesCurrentChildNode[0]['child']['key'] in visitedNodes:
            line = "else:"
            stack.append(noCurrentChildNode[0]['child']['key'])

            visitedNodes.append(currentNode)

            if currentNode == ifNodes[0]:
                completedNoOfPaths = graph.data("MATCH paths = (currentDecision:Student)-[:YES]->"
                                                "(a:Student)-[*]->(commonNode:Student) WHERE currentDecision.key={currentNodeKey} and "
                                                "commonNode.key={commonNodeKey}  RETURN count(paths)",
                                                parameters={"currentNodeKey":
                                                                currentNode,
                                                            "commonNodeKey": currentCommonNode[0]['commonNode']['key']})

                mainIfCompletedNoOfPaths = completedNoOfPaths[0]['count(paths)']
        else:
            line = "if " + currentText.replace("?", "") + ":"
            stack.append(currentNode)
            stack.append(yesCurrentChildNode[0]['child']['key'])

            # no need to do again in no path, as key will be added here in the yes path, so it will anyway be there in the dictionary
            if not ifNodes[0] in visitedNodes:
                if not currentNode in ifDictionary:
                    ifDictionary[currentNode] = noOfPathsToCommonNode
            else:
                if not currentNode in ifDictionary:
                    ifDictionary[currentNode] = mainIfCompletedNoOfPaths + noOfPathsToCommonNode

    return line, currentStructure, mainIfCompletedNoOfPaths


def runDFSAndAddStatementToPyFile(studentAnswerFile):
    # Connect to Graph
    graph = connectToGraph()

    studentStartNodeKey = graph.data(
        "MATCH (node:Student) WHERE node.symbol='Start' RETURN node.key")

    stack = [studentStartNodeKey[0]['node.key']]

    visitedNodes = []

    outputVariableNames = []

    currentStructure = ""

    # maintains common nodes in paths for all if structures
    commonNodes = []

    # maintain all nodes traversed and visited including ones not completed analyzing
    traversedNodes = []

    # this dictionary has keys which are the node keys of ifs under analysis until main if path is joined and values are
    # an indication of the number of times the path joining node must be visited to continue and further reduce the
    # indentation. Yes path will have it corresponding values because yes is analyzed first while no path will have the
    # summation of yes completed ones and the corresponding no path ifs, yes has already been traversed, and that many
    # has to be traversed by the time of no path unindentations.
    ifDictionary = {}

    # maintains if node keys for if-else structures
    ifNodes = []

    doWhileNodes = []

    whileNodes = []

    mainIfCompletedNoOfPaths = 0

    indent = 0

    while stack:
        currentNode = stack.pop()

        traversedNodes.append(currentNode)

        continueWithFlow = 'false'

        if not commonNodes:
            continueWithFlow = 'true'

        while commonNodes:
            currentCommonNode = commonNodes.pop()

            if currentNode == currentCommonNode:
                indent = indent - 1

                currentIfKey = ifNodes.pop()

                if traversedNodes.count(currentNode) < ifDictionary.get(currentIfKey, "none"):
                    commonNodes.append(currentCommonNode)
                    ifNodes.append(currentIfKey)
                    break
                elif traversedNodes.count(currentNode) == ifDictionary.get(currentIfKey, "none"):
                    continueWithFlow = 'true'

                    if not currentNode in commonNodes:
                        traversedNodes[:] = (key for key in traversedNodes if key != currentNode)
                        traversedNodes.append(currentNode)

                    continue
            else:
                continueWithFlow = 'true'
                commonNodes.append(currentCommonNode)
                break

        if not commonNodes:
            ifDictionary = {}
            ifNodes = []
            mainIfCompletedNoOfPaths = 0

        if continueWithFlow == "true":
            currentNodeInfo = graph.data(
                "MATCH (node:Student) WHERE node.key= {key} RETURN node",
                parameters={"key": currentNode})

            currentSymbol = currentNodeInfo[0]['node']['symbol']
            currentText = currentNodeInfo[0]['node']['text']

            currentNodeParents = graph.data(
                "MATCH (parent:Student)-[]->(child:Student) WHERE child.key= {key} RETURN parent",
                parameters={"key": currentNode})

            if indent > 0:
                if doWhileNodes and not whileNodes:
                    if not doWhileNodes[-1] == currentNode:
                        indentLine(indent, studentAnswerFile)
                elif whileNodes and not doWhileNodes:
                    if not whileNodes[-1] == currentNode:
                        indentLine(indent, studentAnswerFile)
                elif doWhileNodes and whileNodes:
                    if not (doWhileNodes[-1] == currentNode or whileNodes[-1] == currentNode):
                        indentLine(indent, studentAnswerFile)
                else:
                    indentLine(indent, studentAnswerFile)

            if currentSymbol == "Input":
                if '\'' in currentText:
                    words = re.split("[,]+", currentText)
                else:
                    words = re.split("[, ]+", currentText)

                for word in words:
                    if not (re.match("input", word, re.IGNORECASE) or re.match("enter", word, re.IGNORECASE) or re.match(
                            "read", word, re.IGNORECASE) or '\'' in word or not word):
                        variable = word.strip()      #.replace(",", "")
                        studentAnswerFile.write(variable + " = float(str(sys.argv[argCount]))\n")
                        if indent > 0:
                            indentLine(indent, studentAnswerFile)
                        studentAnswerFile.write("argCount = argCount + 1\n")

            elif currentSymbol == "Process":
                studentAnswerFile.write(currentText + "\n")
            elif currentSymbol == "Output":
                if '+' in currentText and '\'' in currentText:
                    words = re.split("[+,]+", currentText)
                elif ',' in currentText and '\'' in currentText and not '+' in currentText:
                    words = re.split("[,]+", currentText)
                elif '\'' in currentText and not (',' in currentText or '+' in currentText):
                    words = re.split("[']+", currentText)
                else:
                    words = re.split("[, ]+", currentText)

                print(words)

                for wordSet in words:
                    if not (re.search("output", wordSet, re.IGNORECASE) or re.search("display", wordSet, re.IGNORECASE) or
                            re.search("print", wordSet, re.IGNORECASE) or '\'' in wordSet or not wordSet):
                        variable = wordSet.strip()
                        # + or , means there is a variable
                        if ',' in currentText or '+' in currentText:
                            # output has numeric variables
                            outputVariableNames.append(variable)
                            studentAnswerFile.write("print(" + "str(" + variable + ")" + ")\n")
                        elif not (',' in currentText or '+' in currentText) and '\'' in currentText:
                            # output is just one string value
                            studentAnswerFile.write("print('" + variable + "')\n")
                        else:
                            # output has numeric variable
                            outputVariableNames.append(variable)
                            studentAnswerFile.write("print(" + "str(" + variable + ")" + ")\n")

            elif currentSymbol == "Decision":
                yesCurrentChildNode = graph.data(
                "MATCH (parent:Student)-[:YES]->(child:Student) WHERE parent.key= {key} RETURN child",
                parameters={"key": currentNode})

                yesChildParents = graph.data(
                    "MATCH (parent:Student)-[]->(child:Student) WHERE child.key= {key} RETURN parent",
                    parameters={"key": yesCurrentChildNode[0]['child']['key']})

                noCurrentChildNode = graph.data(
                "MATCH (parent:Student)-[:NO]->(child:Student) WHERE parent.key= {key} RETURN child",
                parameters={"key": currentNode})

                noChildParents = graph.data(
                    "MATCH (parent:Student)-[]->(child:Student) WHERE child.key= {key} RETURN parent",
                    parameters={"key": noCurrentChildNode[0]['child']['key']})

                doWhileFound = "false"

                unindentWhile = "false"

                if ((yesCurrentChildNode[0]['child']['key'] in visitedNodes or noCurrentChildNode[0]['child']['key'] in visitedNodes) \
                                        and traversedNodes.count(currentNode) == 1) or currentNode in doWhileNodes:
                    doWhileFound = "true"

                    if yesCurrentChildNode[0]['child']['key'] in visitedNodes:
                        whileOrNot = "while "
                        if traversedNodes.count(currentNode) == 1:
                            whileNextNode = yesCurrentChildNode[0]['child']['key']
                        elif traversedNodes.count(currentNode) > 1:
                            whileNextNode = noCurrentChildNode[0]['child']['key']
                    elif noCurrentChildNode[0]['child']['key'] in visitedNodes:
                        whileOrNot = "while not "
                        if traversedNodes.count(currentNode) == 1:
                            whileNextNode = noCurrentChildNode[0]['child']['key']
                        elif traversedNodes.count(currentNode) > 1:
                            whileNextNode = yesCurrentChildNode[0]['child']['key']

                    currentStructure = "DoWhile"

                    line, indent, unindentWhile, traversedNodes = handleWhileTypeConversions(currentStructure, stack,
                                                                                             whileNextNode,
                                                                                             traversedNodes,
                                                                                             currentNode, indent,
                                                                                             unindentWhile,
                                                                                             whileOrNot, currentText,
                                                                                             doWhileNodes, visitedNodes)

                else:
                    if (len(whileNodes) == 0 and traversedNodes.count(currentNode) == 1) or \
                            (len(whileNodes) == 1 and traversedNodes.count(currentNode) == 2):
                        loopPath = graph.data("MATCH (currentNode:Student)-[r:YES|NO]->(nextNode:Student)-[*]->" +
                                              "(currentNode:Student) WHERE currentNode.key = {currentNodeKey} RETURN DISTINCT TYPE(r)",
                                              parameters={"currentNodeKey": currentNode})
                    elif (len(whileNodes) == 1 and traversedNodes.count(currentNode) == 1) or \
                            (len(whileNodes) == 2 and traversedNodes.count(currentNode) == 2):
                        loopPath = graph.data("MATCH path = (currentNode:Student)-[r:YES|NO]->(nextNode:Student)-[*]->"
                                              "(currentNode:Student) WHERE currentNode.key = {currentNodeKey} "
                                              "WITH path, r MATCH (previousIfNode: Student) WHERE previousIfNode.key = "
                                              "{previousIfNodeKey} AND NOT previousIfNode IN NODES(path) RETURN TYPE(r)",
                                              parameters={"currentNodeKey": currentNode,
                                                          "previousIfNodeKey": whileNodes[0]})
                    elif (len(whileNodes) == 2 and traversedNodes.count(currentNode) == 1) or \
                            (len(whileNodes) == 3 and traversedNodes.count(currentNode) == 2):
                        loopPath = graph.data("MATCH path = (currentNode:Student)-[r:YES|NO]->(nextNode:Student)-[*]->"
                                              "(currentNode:Student) WHERE currentNode.key = {currentNodeKey} "
                                              "WITH path, r MATCH (previousIfNodeOne: Student), "
                                              "(previousIfNodeTwo: Student) WHERE (previousIfNodeOne.key = "
                                              "{previousIfNodeOneKey} AND NOT previousIfNodeOne IN NODES(path)) AND "
                                              "(previousIfNodeTwo.key = {previousIfNodeTwoKey} AND NOT previousIfNodeTwo "
                                              "IN NODES(path)) RETURN TYPE(r)",
                                              parameters={"currentNodeKey": currentNode,
                                                          "previousIfNodeOneKey": whileNodes[0],
                                                          "previousIfNodeTwoKey": whileNodes[1]})

                    if not loopPath:
                        line, currentStructure, mainIfCompletedNoOfPaths = handleIfTypeConversions(graph, stack,
                                                                                                   currentNode,
                                                                                                   traversedNodes,
                                                                                                   noChildParents,
                                                                                                   yesChildParents,
                                                                                                   noCurrentChildNode,
                                                                                                   yesCurrentChildNode,
                                                                                                   currentText,
                                                                                                   commonNodes,
                                                                                                   ifNodes,
                                                                                                   ifDictionary,
                                                                                                   visitedNodes,
                                                                                                   mainIfCompletedNoOfPaths)
                    else:
                        if commonNodes or whileNodes or doWhileNodes:
                            if (len(whileNodes) == 0 and traversedNodes.count(currentNode) == 1) or \
                                    (len(whileNodes) == 1 and traversedNodes.count(currentNode) == 2) or \
                                    (len(whileNodes) == 0 and traversedNodes.count(currentNode) == 2):
                                loopPathLength = graph.data(
                                    "MATCH path = (currentNode:Student)-[r:YES|NO]->(nextNode:Student)-[*]->" +
                                    "(currentNode:Student) WHERE currentNode.key = " +
                                    "{currentNodeKey} RETURN length(path)", parameters={"currentNodeKey": currentNode})
                            elif (len(whileNodes) == 1 and traversedNodes.count(currentNode) == 1) or \
                                    (len(whileNodes) == 2 and traversedNodes.count(currentNode) == 2):
                                loopPathLength = graph.data(
                                    "MATCH path = (currentNode:Student)-[r:YES|NO]->(nextNode:Student)-[*]->" +
                                    "(currentNode:Student) WHERE currentNode.key = {currentNodeKey} WITH path, r " +
                                    "MATCH (previousIfNode:Student) WHERE previousIfNode.key = {previousIfNodeKey} " +
                                    "AND NOT previousIfNode IN NODES(path) RETURN length(path)",
                                    parameters={"currentNodeKey": currentNode, "previousIfNodeKey": whileNodes[0]})
                            elif (len(whileNodes) == 2 and traversedNodes.count(currentNode) == 1) or \
                                    (len(whileNodes) == 3 and traversedNodes.count(currentNode) == 2):
                                loopPathLength = graph.data(
                                    "MATCH path = (currentNode:Student)-[r:YES|NO]->(nextNode:Student)-[*]->" +
                                    "(currentNode:Student) WHERE currentNode.key = {currentNodeKey} WITH path, r " +
                                    "MATCH (previousIfNodeOne:Student), "
                                    "(previousIfNodeTwo:Student) WHERE (previousIfNodeOne.key = "
                                    "{previousIfNodeOneKey} AND NOT previousIfNodeOne IN NODES(path)) AND "
                                    "(previousIfNodeTwo.key = {previousIfNodeTwoKey} AND NOT previousIfNodeTwo "
                                    "IN NODES(path)) RETURN length(path)",
                                    parameters={"currentNodeKey": currentNode,
                                                "previousIfNodeOneKey": whileNodes[0],
                                                "previousIfNodeTwoKey": whileNodes[1]})

                            curCommonNodePathLength = graph.data(
                                "MATCH path1 = (currentDecision:Student)-[:YES]->(a:Student)-[*]->(commonNode:Student), " +
                                "path2 = (currentDecision:Student)-[:NO]->(b:Student)-[*]->" +
                                "(commonNode:Student) WHERE currentDecision.key={currentNodeKey} and path1 <> path2 " +
                                "and currentDecision <> commonNode RETURN length(path2)",
                                parameters={"currentNodeKey": currentNode})

                            if not curCommonNodePathLength:
                                curCommonNodePathLength = graph.data(
                                    "MATCH path1 = (currentDecision:Student)-[:YES]->(a:Student)-[*]->" +
                                    "(commonNode:Student), path2 = (currentDecision:Student)-[:NO]->" +
                                    "(commonNode:Student) WHERE currentDecision.key={currentNodeKey} and " +
                                    "path1 <> path2 and currentDecision <> commonNode RETURN length(path2)",
                                    parameters={"currentNodeKey": currentNode})

                            if not curCommonNodePathLength:
                                curCommonNodePathLength = graph.data(
                                    "MATCH path1 = (currentDecision:Student)-[:YES]->(commonNode:Student), " +
                                    "path2 = (currentDecision:Student)-[:NO]->(b:Student)-[*]->(commonNode:Student) " +
                                    "WHERE currentDecision.key={currentNodeKey} and path1 <> path2 and " +
                                    "currentDecision <> commonNode RETURN length(path1)",
                                    parameters={"currentNodeKey": currentNode})

                            if not curCommonNodePathLength:
                                whileOrNot, whileNextNode, currentStructure = handleWhileTraversal(loopPath,
                                                                                                   traversedNodes,
                                                                                                   currentNode,
                                                                                                   yesCurrentChildNode,
                                                                                                   noCurrentChildNode)

                                line, indent, unindentWhile, traversedNodes = handleWhileTypeConversions(
                                    currentStructure, stack, whileNextNode,
                                    traversedNodes, currentNode, indent,
                                    unindentWhile, whileOrNot, currentText,
                                    whileNodes, visitedNodes)
                            elif not loopPathLength:
                                line, currentStructure, mainIfCompletedNoOfPaths = handleIfTypeConversions(graph,
                                                                                                           stack,
                                                                                                           currentNode,
                                                                                                           traversedNodes,
                                                                                                           noChildParents,
                                                                                                           yesChildParents,
                                                                                                           noCurrentChildNode,
                                                                                                           yesCurrentChildNode,
                                                                                                           currentText,
                                                                                                           commonNodes,
                                                                                                           ifNodes,
                                                                                                           ifDictionary,
                                                                                                           visitedNodes,
                                                                                                           mainIfCompletedNoOfPaths)
                            else:
                                if loopPathLength[0]['length(path)'] > curCommonNodePathLength[0]['length(path2)']:
                                    line, currentStructure, mainIfCompletedNoOfPaths = handleIfTypeConversions(graph,
                                                                                                               stack,
                                                                                                               currentNode,
                                                                                                               traversedNodes,
                                                                                                               noChildParents,
                                                                                                               yesChildParents,
                                                                                                               noCurrentChildNode,
                                                                                                               yesCurrentChildNode,
                                                                                                               currentText,
                                                                                                               commonNodes,
                                                                                                               ifNodes,
                                                                                                               ifDictionary,
                                                                                                               visitedNodes,
                                                                                                               mainIfCompletedNoOfPaths)
                                else:
                                    whileOrNot, whileNextNode, currentStructure = handleWhileTraversal(loopPath,
                                                                                                       traversedNodes,
                                                                                                       currentNode,
                                                                                                       yesCurrentChildNode,
                                                                                                       noCurrentChildNode)

                                    line, indent, unindentWhile, traversedNodes = handleWhileTypeConversions(
                                        currentStructure, stack, whileNextNode,
                                        traversedNodes, currentNode, indent,
                                        unindentWhile, whileOrNot, currentText,
                                        whileNodes, visitedNodes)
                        else:
                            whileOrNot, whileNextNode, currentStructure = handleWhileTraversal(loopPath, traversedNodes,
                                                                                               currentNode,
                                                                                               yesCurrentChildNode,
                                                                                               noCurrentChildNode)

                            line, indent, unindentWhile, traversedNodes = handleWhileTypeConversions(currentStructure,
                                                                                                     stack,
                                                                                                     whileNextNode,
                                                                                                     traversedNodes,
                                                                                                     currentNode,
                                                                                                     indent,
                                                                                                     unindentWhile,
                                                                                                     whileOrNot,
                                                                                                     currentText,
                                                                                                     whileNodes,
                                                                                                     visitedNodes)

                if unindentWhile == "false":
                    studentAnswerFile.write(line + "\n")
                    indent = indent + 1

            if not (currentSymbol == "Decision" or currentSymbol == 'End'):
                currentChildNodes = graph.data(
                    "MATCH (parent:Student)-[:TO]->(child:Student) WHERE parent.key= {key} RETURN child",
                    parameters={"key": currentNode})

                stack.append(currentChildNodes[0]['child']['key'])
                visitedNodes.append(currentNode)

    return outputVariableNames


def executeStudentAnswerProgram(outputVariableNames,
                                flowchartQuestionId):
    desiredProgramExecution = "true"

    connection = connectToMySQL()
    cur = connection.cursor()
    cur.execute("SELECT inputs, outputs FROM flowchart_question WHERE 	flowchartqId = %s", (flowchartQuestionId))
    resultSet = cur.fetchone()
    cur.close()
    connection.close()

    outputs = resultSet[1].split(",")

    programOutput = {}

    sys.argv = ["studentAnswer.py"]

    if resultSet[0]:
        inputs = resultSet[0].split(",")

        for input in inputs:
            sys.argv.append(float(input))

    if not os.path.exists("studentAnswer.py"):
        print('file does not exist in current path')
    else:
        print('file exists')

    # redirect the standard output to a string until the end of the exec method call
    old_stdout = sys.stdout
    redirected_programOutput = sys.stdout = StringIO()
    try:
        exec(open("studentAnswer.py").read())
    except SystemExit:
        desiredProgramExecution = "false"
    except:
        desiredProgramExecution = "false"
    sys.stdout = old_stdout

    if desiredProgramExecution == "true":
        redirected_programOutput = redirected_programOutput.getvalue()
        # redirected output has new line characters to separate outputs. Therefore, split and store them for later use.
        redirected_programOutput = redirected_programOutput.splitlines()

        count = 0

        for output in outputs:
            if len(redirected_programOutput) > count:
                if not all(x.isalpha() or x.isspace() for x in output):
                    if not float(output) == float(redirected_programOutput[count]):
                        desiredProgramExecution = "false"
                        break
                else:
                    if not output == redirected_programOutput[count]:
                        desiredProgramExecution = "false"
                        break

                count = count + 1
            else:
                # this means that the number of outputs of the teacher and student are not the same
                desiredProgramExecution = "false"
                break

    return desiredProgramExecution



def convertFlowchartToProgram(flowchartQuestionId):
    studentAnswerFile = open("studentAnswer.py", "w")
    # studentAnswerFile.write("import sys\nimport time\n")
    studentAnswerFile.write("import sys\n")
    studentAnswerFile.write("argCount = 1\n")

    try:
        outputVariableNames = runDFSAndAddStatementToPyFile(studentAnswerFile)
        possibleToGenerateProgram = "true"
    except:
        possibleToGenerateProgram = "false"

    studentAnswerFile.close()

    desiredProgramExecution = "false"

    if possibleToGenerateProgram == "true":
        desiredProgramExecution = executeStudentAnswerProgram(outputVariableNames, flowchartQuestionId)

    if desiredProgramExecution == "true":
        print("Desired correct program execution")
    elif desiredProgramExecution == "false":
        print("Incorrect program execution")

    if os.path.isfile('studentAnswer.py'):
        os.remove('studentAnswer.py')

    return desiredProgramExecution