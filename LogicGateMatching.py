import pymysql

from CreateGraph import connectToGraph

from LogicGateSimulation import simulateLogicGate

import json

from DbConnection import connectToMySQL


def detectUndetectedGates(caller,
                          graph,
                          nodeStack,
                          visitedNodeSet,
                          totNoOfIncorrectNodes):

    # copy visitedNodeSet to handledNodeSet in this way to prevent it being referenced
    handledNodeSet = visitedNodeSet[:]

    while nodeStack:

        currentNode = nodeStack.pop()

        if caller == "additionalNodes" or caller == "addOrSubNodes":
            currentNodeChildNodes = graph.data(
                "MATCH (parent:Student)-[:TO]->(child:Student) WHERE parent.key = {key} RETURN child",
                parameters={"key": currentNode})
        elif caller == "deletedNodes" or caller == "delOrSubNodes" or caller == "substitutedNodes":
            currentNodeChildNodes = graph.data(
                "MATCH (parent:Teacher)-[:TO]->(child:Teacher) WHERE parent.key = {key} RETURN child",
                parameters={"key": currentNode})

        currentNodeChildNodesList = list(currentNodeChildNodes)

        for childNode in currentNodeChildNodesList:
            if not childNode['child']['symbol'] == 'output':
                if not childNode['child']['key'] in handledNodeSet:
                    totNoOfIncorrectNodes = totNoOfIncorrectNodes + 1
                    nodeStack.append(childNode['child']['key'])
                    handledNodeSet.append(childNode['child']['key'])
                elif childNode['child']['key'] in handledNodeSet:
                    continue

    return totNoOfIncorrectNodes

def getAllStudentNodeKeysList():
    graph = connectToGraph()

    studentNodes = graph.data(
        "MATCH (node:Student) RETURN node.key")

    studentNodesList = []

    count = 0
    while count < len(studentNodes):
        studentNodesList.append(studentNodes[count]['node.key'])
        count = count + 1

    return studentNodesList


def getTotalNoOfTeacherNodes():
    graph = connectToGraph()

    studentNodes = graph.data(
        "MATCH (node:Teacher) RETURN node.key")

    return len(studentNodes)


def allocateMarksToLogicGateAnswerAndSaveToDatabase(matchedCompletedStudentNodes,
                                                    noOfMatchedNodes,
                                                    noOfAdditionalNodes,
                                                    noOfDeletedNodes,
                                                    noOfSubstitutedNodes,
                                                    totNoOfOtherIncorrectNodes,
                                                    feedback,
                                                    logicGateQuestionId, 
                                                    studentAnswerId):
    connection = connectToMySQL()
    cur = connection.cursor()
    cur.execute("SELECT symbolMark, sequenceMark FROM logic_gate_question WHERE logicgateqId = %s", (logicGateQuestionId))
    resultSet = cur.fetchone()
    print('starting mark allocation...')

    symbolMark = resultSet[0]
    sequenceMark = resultSet[1]

    sequenceMarkForAddDeleteSubDeductions = (80 / 100) * sequenceMark

    totalAddDeleteSubDiff = noOfAdditionalNodes + noOfDeletedNodes + noOfSubstitutedNodes + totNoOfOtherIncorrectNodes

    scoredSymbolMark = noOfMatchedNodes * symbolMark

    if noOfMatchedNodes == 0:
        scoredSequenceMark = 0
    else:
        # maximum number of errors for additions and deletions that are allowed is 6
        if totalAddDeleteSubDiff <= 6:
            scoredSequenceMark = sequenceMark - (totalAddDeleteSubDiff / 6) * sequenceMarkForAddDeleteSubDeductions
        else:
            scoredSequenceMark = sequenceMark - sequenceMarkForAddDeleteSubDeductions

    scoredFullMark = scoredSymbolMark + scoredSequenceMark

    # save matched correct gates to database
    matchedGatesStr = ""
    count = 0
    while count < len(matchedCompletedStudentNodes):
        matchedGatesStr = matchedGatesStr + str(matchedCompletedStudentNodes[count]) + ","
        count = count + 1

    matchedGatesStr = matchedGatesStr[:-1]

    cur.execute("UPDATE logic_gate_stud_answer SET symbolMark = %s, sequenceMark = %s, matchedGates = %s WHERE logicgateStudAnsId = %s",
                (scoredSymbolMark, scoredSequenceMark, matchedGatesStr, studentAnswerId))

    cur.execute("UPDATE student_answer SET scoredMark = %s, feedback = %s, markedStatus = %s WHERE studAnswerId = %s",
                (scoredFullMark, feedback, "true", studentAnswerId))
    cur.close()
    connection.close()



def markStudBFSLogicGateAnswer():
    # Connect to Graph
    graph = connectToGraph()

    answerDiagramCorrect = 'false'

    teacherInputNodes = graph.data(
        "MATCH (node:Teacher) WHERE node.symbol='input' RETURN node")
    studentInputNodes = graph.data(
        "MATCH (node:Student) WHERE node.symbol='input' RETURN node")

    teacherQueue = [teacherInputNodes[0]['node']['key']]

    count = 0
    while count < len(studentInputNodes):
        if studentInputNodes[count]['node']['text'] == teacherInputNodes[0]['node']['text']:
            studentQueue = [studentInputNodes[count]['node']['key']]
        count = count + 1

    count = 1
    while count < len(teacherInputNodes):
        teacherQueue.insert(0, teacherInputNodes[count]['node']['key'])

        studCount = 0
        while studCount < len(studentInputNodes):
            if studentInputNodes[studCount]['node']['text'] == teacherInputNodes[count]['node']['text']:
                studentQueue.insert(0, studentInputNodes[studCount]['node']['key'])
            studCount = studCount + 1

        count = count + 1

    childlessTeacherOtherParents = []
    childHavingTeacherOtherParents = []

    childlessStudentOtherParents = []
    childHavingStudentOtherParents = []

    # maintains all matched and completed nodes so far(the ones which have been removed from the queue after completion)
    matchedCompletedTeacherNodes = []
    matchedCompletedStudentNodes = []

    # each time a student gate is visited, it is added to this
    visitedStudentNodes = []

    matchedTeacherLevelNodes = []
    matchedStudentLevelNodes = []

    additionalNodes = []
    deletedNodes = []
    substitutedNodes = []
    addOrSubNodes = []
    delOrSubNodes = []

    errorneousTeacherNodes = []
    errorneousStudentNodes = []

    totNoOfAdditionalNodes = 0
    totNoOfDeletedNodes = 0
    totNoOfSubstitutedNodes = 0
    totNoOfOtherIncorrectNodes = 0

    feedback = ""

    # maintains parents to see if all its children has been traversed before and so that it can be removed from the queue
    # traversedChildMatchFoundNodes = []

    while teacherQueue and studentQueue:   # or

        teacherCurrent = teacherQueue.pop()
        studentCurrent = studentQueue.pop()

        currentTeacherNodeInfo = graph.data(
            "MATCH (node:Teacher) WHERE node.key= {key} RETURN node",
            parameters={"key": teacherCurrent})

        currentStudentNodeInfo = graph.data(
            "MATCH (node:Student) WHERE node.key= {key} RETURN node",
            parameters={"key": studentCurrent})

        if currentTeacherNodeInfo[0]['node']['symbol'] == "output":
            if currentStudentNodeInfo[0]['node']['symbol'] == "output":
                feedback = feedback + 'The output and the connections to it are correct. '

                answerDiagramCorrect = 'true'
                break

        teacherChildNodes = graph.data(
            "MATCH (parent:Teacher)-[:TO]->(child:Teacher) WHERE parent.key= {key} RETURN child",
            parameters={"key": teacherCurrent})

        studentChildNodes = graph.data(
            "MATCH (parent:Student)-[:TO]->(child:Student) WHERE parent.key= {key} RETURN child",
            parameters={"key": studentCurrent})

        for teacherChild in teacherChildNodes:
            # get all parents of current teacher child node under analysis except the current teacher parent node
            teacherChildParents = graph.data(
                "MATCH (parent:Teacher)-[:TO]->(child:Teacher) WHERE child.key= {key} AND parent.key <> {parentKey} RETURN parent",
                parameters={"key": teacherChild['child']['key'], "parentKey": teacherCurrent})

            teacherChildParentsList = list(teacherChildParents)

            childlessTeacherOtherParents = []
            childHavingTeacherOtherParents = []

            for teacherChildParent in teacherChildParentsList:
                teacherChildParentChildrenNodes = graph.data(
                    "MATCH (parent:Teacher)-[:TO]->(child:Teacher) WHERE parent.key= {parentKey} AND child.key <> {childKey} RETURN child",
                    parameters ={"parentKey": teacherChildParent['parent']['key'], "childKey": teacherChild['child']['key']})

                # check whether other teacher parents have other children besides current child
                if not teacherChildParentChildrenNodes:
                    childlessTeacherOtherParents.append(teacherChildParent)
                else:
                    childHavingTeacherOtherParents.append(teacherChildParent)

            for studentChild in studentChildNodes:
                if currentTeacherNodeInfo[0]['node']['symbol'] == currentStudentNodeInfo[0]['node']['symbol'] and \
                        teacherChild['child']['symbol'] == studentChild['child']['symbol']:

                    studentChildParents = graph.data(
                        "MATCH (parent:Student)-[:TO]->(child:Student) WHERE child.key= {key} AND parent.key <> {parentKey} RETURN parent",
                        parameters={"key": studentChild['child']['key'], "parentKey": studentCurrent})

                    studentChildParentsList = list(studentChildParents)

                    childlessStudentOtherParents = []
                    childHavingStudentOtherParents = []

                    for studentChildParent in studentChildParentsList:
                        studentChildParentChildrenNodes = graph.data(
                            "MATCH (parent:Student)-[:TO]->(child:Student) WHERE parent.key= {parentKey} AND child.key <> {childKey} RETURN child",
                            parameters={"parentKey": studentChildParent['parent']['key'],
                                        "childKey": studentChild['child']['key']})

                        # check whether other student parents have other children besides current child
                        if not studentChildParentChildrenNodes:
                            childlessStudentOtherParents.append(studentChildParent)
                        else:
                            childHavingStudentOtherParents.append(studentChildParent)

                    if len(childlessTeacherOtherParents) == len(childlessStudentOtherParents) and \
                            len(childHavingTeacherOtherParents) == len(childHavingStudentOtherParents):
                        if currentStudentNodeInfo[0]['node']['symbol'] == "input" and not currentStudentNodeInfo[0]['node']['key'] in matchedCompletedStudentNodes:
                            matchedCompletedTeacherNodes.append(teacherCurrent)
                            matchedCompletedStudentNodes.append(studentCurrent)


                        childlessStudentOtherParentsNotInQueue = []

                        # if this gate has been visited once, then already childless other parents have been removed if they were in the queue
                        # so no need to do it again and it cannot be done
                        if not studentChild['child']['key'] in visitedStudentNodes:
                            # remove childless other teacher parents and remove childless other student parents
                            for childlessTeacherNode in childlessTeacherOtherParents:
                
                                for childlessStudentNode in childlessStudentOtherParents:
                                        if childlessTeacherNode['parent']['symbol'] == childlessStudentNode['parent']['symbol']:

                                            if childlessTeacherNode['parent']['key'] in teacherQueue and\
                                                    childlessStudentNode['parent']['key'] in studentQueue:
                                                teacherQueue.remove(childlessTeacherNode['parent']['key'])
                                                studentQueue.remove(childlessStudentNode['parent']['key'])

                                                if childlessStudentNode['parent']['symbol'] == "input" and not childlessStudentNode['parent']['key'] in matchedCompletedStudentNodes:
                                                    matchedCompletedTeacherNodes.append(childlessTeacherNode['parent']['key'])
                                                    matchedCompletedStudentNodes.append(childlessStudentNode['parent']['key'])

                                                visitedStudentNodes.append(studentChild['child']['key'])
                                            else:
                                                childlessStudentOtherParentsNotInQueue.append(childlessStudentNode['parent']['key'])


                        visitedStudentNodes.append(studentChild['child']['key'])

                        # insert matched gate to queue
                        if len(childlessStudentOtherParentsNotInQueue) == 0 and \
                                visitedStudentNodes.count(studentChild['child']['key']) == (len(studentChildParents) + 1):
                            teacherQueue.insert(0, teacherChild['child']['key'])
                            studentQueue.insert(0, studentChild['child']['key'])

                            if not studentChild['child']['symbol'] == 'output':  # and not studentChild['child']['key'] in matchedCompletedStudentNodes
                                feedback = feedback + 'The gate: ' + studentChild['child'][
                                    'symbol'].upper() + ' and its input connections are correct. '

                            matchedCompletedTeacherNodes.append(teacherChild['child']['key'])
                            matchedCompletedStudentNodes.append(studentChild['child']['key'])

                        if len(teacherChildNodes) == len(studentChildNodes) or len(teacherChildNodes) > len(studentChildNodes):
                            matchedTeacherLevelNodes.append(teacherChild['child']['key'])
                        elif len(teacherChildNodes) < len(studentChildNodes):
                            matchedStudentLevelNodes.append(studentChild['child']['key'])

                        childlessTeacherOtherParents = []
                        childlessStudentOtherParents = []
                        childHavingTeacherOtherParents = []
                        childHavingStudentOtherParents = []

                        childlessStudentOtherParentsNotInQueue = []

                        break

        if len(teacherChildNodes) == len(studentChildNodes):
            if not len(teacherChildNodes) == len(matchedTeacherLevelNodes):
                for teacherChild in teacherChildNodes:
                    if not teacherChild['child']['key'] in matchedTeacherLevelNodes and not teacherChild['child']['key'] in errorneousTeacherNodes:
                        substitutedNodes.append(teacherChild['child']['key'])
                        totNoOfSubstitutedNodes = totNoOfSubstitutedNodes + 1
                        errorneousTeacherNodes.append(teacherChild['child']['key'])

                for studentChild in studentChildNodes:
                    if not studentChild['child']['key'] in matchedStudentLevelNodes:
                        errorneousStudentNodes.append(studentChild['child']['key'])
        elif len(teacherChildNodes) > len(studentChildNodes):
            if len(matchedTeacherLevelNodes) < len(studentChildNodes):
                for teacherChild in teacherChildNodes:
                    if not teacherChild['child']['key'] in matchedTeacherLevelNodes and not teacherChild['child']['key'] in errorneousTeacherNodes:
                        delOrSubNodes.append(teacherChild['child']['key'])
                        totNoOfOtherIncorrectNodes = totNoOfOtherIncorrectNodes + 1
                        errorneousTeacherNodes.append(teacherChild['child']['key'])
            elif len(matchedTeacherLevelNodes) == len(studentChildNodes):
                for teacherChild in teacherChildNodes:
                    if not teacherChild['child']['key'] in matchedTeacherLevelNodes and not teacherChild['child']['key'] in errorneousTeacherNodes:
                        deletedNodes.append(teacherChild['child']['key'])
                        totNoOfDeletedNodes = totNoOfDeletedNodes + 1
                        errorneousTeacherNodes.append(teacherChild['child']['key'])

            for studentChild in studentChildNodes:
                if not studentChild['child']['key'] in matchedStudentLevelNodes:
                    errorneousStudentNodes.append(studentChild['child']['key'])
        elif len(teacherChildNodes) < len(studentChildNodes):
            if len(matchedStudentLevelNodes) == len(teacherChildNodes):
                for studentChild in studentChildNodes:
                    if not studentChild['child']['key'] in matchedStudentLevelNodes and not studentChild['child']['key'] in errorneousStudentNodes:
                        additionalNodes.append(studentChild['child']['key'])
                        totNoOfAdditionalNodes = totNoOfAdditionalNodes + 1
                        errorneousStudentNodes.append(studentChild['child']['key'])
            elif len(matchedStudentLevelNodes) < len(teacherChildNodes):
                for studentChild in studentChildNodes:
                    if not studentChild['child']['key'] in matchedStudentLevelNodes and not studentChild['child']['key'] in errorneousStudentNodes:
                        addOrSubNodes.append(studentChild['child']['key'])
                        totNoOfOtherIncorrectNodes = totNoOfOtherIncorrectNodes + 1
                        errorneousStudentNodes.append(studentChild['child']['key'])

            for teacherChild in teacherChildNodes:
                if not teacherChild['child']['key'] in matchedTeacherLevelNodes:
                    errorneousTeacherNodes.append(teacherChild['child']['key'])

        matchedTeacherLevelNodes = []
        matchedStudentLevelNodes = []

    # handles additional nodes down an additional node starting path
    if additionalNodes:
        totNoOfAdditionalNodes = detectUndetectedGates("additionalNodes", graph, additionalNodes,
                                                        matchedCompletedStudentNodes, totNoOfAdditionalNodes)

    # handles deleted nodes down a deleted node starting path
    if deletedNodes:
        totNoOfDeletedNodes = detectUndetectedGates("deletedNodes", graph, deletedNodes,
                                                    matchedCompletedTeacherNodes, totNoOfDeletedNodes)

    # handles substituted nodes down a substituted node starting path
    if substitutedNodes:
        totNoOfSubstitutedNodes = detectUndetectedGates("substitutedNodes", graph, substitutedNodes,
                                                        matchedCompletedTeacherNodes, totNoOfSubstitutedNodes)

    # handles additional/substituted nodes down a additional/substituted node starting path
    if addOrSubNodes:
        totNoOfOtherIncorrectNodes = detectUndetectedGates("addOrSubNodes", graph, addOrSubNodes,
                                                           matchedCompletedStudentNodes, totNoOfOtherIncorrectNodes)

    # handles deleted/substituted nodes down a deleted/substituted node starting path
    if delOrSubNodes:
        totNoOfOtherIncorrectNodes = detectUndetectedGates("delOrSubNodes", graph, delOrSubNodes,
                                                           matchedCompletedTeacherNodes, totNoOfOtherIncorrectNodes)


    if totNoOfAdditionalNodes == 0 and totNoOfDeletedNodes == 0 and totNoOfSubstitutedNodes == 0 and \
            totNoOfOtherIncorrectNodes == 0:
        feedback = feedback + "Excellent Job! All the inputs, gates, output, and the connections are correct! "

    feedback = feedback + "Please refer your answer diagram for feedback on where you went wrong. Green " +\
               "indicates correct gates and connections while Red indicates wrong gates and connections. " +\
               "Please note that any input(to a gate) connected to a wrong gate(a gate wbich has wrong " +\
               "connections even if the symbol is the same) is identified wrong by the system and in the highlighted gate feedback. "

    return matchedCompletedStudentNodes,  totNoOfAdditionalNodes, totNoOfDeletedNodes, \
           totNoOfSubstitutedNodes, totNoOfOtherIncorrectNodes, feedback, answerDiagramCorrect


def markLogicGateAnswer(logicGateQuestionId, studentAnswerId, isExactMatch, noOfInputs):
    if isExactMatch == "true":  # resultSet[0]
        matchedCompletedStudentNodes, noOfAdditionalNodes, noOfDeletedNodes, noOfSubstitutedNodes, totNoOfOtherIncorrectNodes, \
        feedback, answerDiagramCorrect = markStudBFSLogicGateAnswer()
        allocateMarksToLogicGateAnswerAndSaveToDatabase(matchedCompletedStudentNodes, len(matchedCompletedStudentNodes), \
                                                        noOfAdditionalNodes, noOfDeletedNodes, \
                                                        noOfSubstitutedNodes, totNoOfOtherIncorrectNodes, feedback, \
                                                        logicGateQuestionId, studentAnswerId)
    elif isExactMatch == "false":
        matchedCompletedStudentNodes, noOfAdditionalNodes, noOfDeletedNodes, noOfSubstitutedNodes, totNoOfOtherIncorrectNodes, \
        feedback, answerDiagramCorrect = markStudBFSLogicGateAnswer()

        noOfMatchedNodes = len(matchedCompletedStudentNodes)

        if answerDiagramCorrect == "false":
            noOfMatchedCombinations = simulateLogicGate("Student", noOfInputs, logicGateQuestionId)

            if (noOfInputs == 1 and noOfMatchedCombinations == 2) or (noOfInputs == 2 and noOfMatchedCombinations == 4)\
                    or (noOfInputs == 3 and noOfMatchedCombinations == 8):
                matchedCompletedStudentNodes.clear()
                matchedCompletedStudentNodes = getAllStudentNodeKeysList()
                noOfMatchedNodes = getTotalNoOfTeacherNodes()
                noOfAdditionalNodes = 0
                noOfDeletedNodes = 0
                noOfSubstitutedNodes = 0
                totNoOfOtherIncorrectNodes = 0

                feedback = feedback + "Your answer is an alternative to the teacher's answer, and it is correct. "
            else:
                feedback = feedback + "Your answer is wrong when compared to the teacher's answer, and also, it is not " + \
                           "an alternative to the teacher's answer. "

        allocateMarksToLogicGateAnswerAndSaveToDatabase(matchedCompletedStudentNodes, noOfMatchedNodes, noOfAdditionalNodes, noOfDeletedNodes,
                                                        noOfSubstitutedNodes, totNoOfOtherIncorrectNodes, feedback, \
                                                        logicGateQuestionId, studentAnswerId)