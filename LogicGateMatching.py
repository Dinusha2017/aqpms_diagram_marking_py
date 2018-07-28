import pymysql

from CreateGraph import createNodes, createRelationships, connectToGraph

from LogicGateSimulation import simulateLogicGate

import json

mySQLhostname = '206.189.209.170'
mySQLusername = 'aqpmsuser'
mySQLpassword = 'aqpms'
mySQLdatabase = 'question_marking_system'

def createTeacherLogicGateGraph():
    connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)
    cur = connection.cursor()
    cur.execute("SELECT answerDiagram FROM logic_gate_question WHERE logicgateqId = '%d'" % (1))
    resultSet = cur.fetchone()
    cur.close()
    connection.close()

    jsonData = json.loads(resultSet[0])

    createNodes(jsonData, "Teacher", "LogicGate")
    createRelationships(jsonData, "Teacher")


def createStudentLogicGateGraph():
    connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)
    cur = connection.cursor()
    cur.execute("SELECT answerDiagram FROM logic_gate_stud_answer WHERE logicgateStudAnsId = '%d'" % (1))
    resultSet = cur.fetchone()
    cur.close()
    connection.close()

    jsonData = json.loads(resultSet[0])

    print(jsonData)

    createNodes(jsonData, "Student", "LogicGate")
    createRelationships(jsonData, "Student")


# createTeacherLogicGateGraph()
# createStudentLogicGateGraph()


def detectUndetectedGates(caller,
                          graph,
                          nodeStack,
                          visitedNodeSet,
                          totNoOfIncorrectNodes):

    # copy visitedNodeSet to handledNodeSet in this way to prevent it being referenced
    handledNodeSet = visitedNodeSet[:]

    while nodeStack:

        currentNode = nodeStack.pop()

        print('caller')
        print(caller)
        print('detectUndetectedGates currentNode')
        print(currentNode)

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



# getAllStudentNodeKeysList()


def getTotalNoOfTeacherNodes():
    graph = connectToGraph()

    studentNodes = graph.data(
        "MATCH (node:Teacher) RETURN node.key")

    return len(studentNodes)

# print(getTotalNoOfTeacherNodes())



def allocateMarksToLogicGateAnswerAndSaveToDatabase(matchedCompletedStudentNodes,
                                                    noOfMatchedNodes,
                                                    noOfAdditionalNodes,
                                                    noOfDeletedNodes,
                                                    noOfSubstitutedNodes,
                                                    totNoOfOtherIncorrectNodes,
                                                    feedback,
                                                    logicGateQuestionId, 
                                                    studentAnswerId):
    connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)
    cur = connection.cursor()
    cur.execute("SELECT symbolMark, sequenceMark FROM logic_gate_question WHERE logicgateqId = %s", (logicGateQuestionId))
    resultSet = cur.fetchone()
    print('starting mark allocation...')

    symbolMark = resultSet[0]
    sequenceMark = resultSet[1]

    sequenceMarkForAddDeleteSubDeductions = (80 / 100) * sequenceMark
    print('sequenceMarkForAddDeleteDeductions: ' + str(sequenceMarkForAddDeleteSubDeductions))

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

    print(scoredSymbolMark)
    print(scoredSequenceMark)
    print('no of matched nodes in allocateMarksToLogicGateAnswerAndSaveToDatabase')
    print(noOfMatchedNodes)
    print(noOfAdditionalNodes)
    print(noOfDeletedNodes)
    print(noOfSubstitutedNodes)
    print(totNoOfOtherIncorrectNodes)

    # save matched correct gates to database
    matchedGatesStr = ""
    count = 0
    while count < len(matchedCompletedStudentNodes):
        print(matchedGatesStr)
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

    print(teacherInputNodes[0]['node']['key'])
    print(studentInputNodes)

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

        print(teacherCurrent)
        print(currentTeacherNodeInfo[0]['node']['symbol'])

        if currentTeacherNodeInfo[0]['node']['symbol'] == "output":
            print('^^^^^^^INSIDE teacher pop is output')
            # studentCurrent = studentQueue.pop()

            # currentStudentNodeSymbol = graph.data(
            #     "MATCH (node:Student) WHERE node.key= {key} RETURN node.symbol",
            #     parameters={"key": studentCurrent})

            if currentStudentNodeInfo[0]['node']['symbol'] == "output":
                feedback = feedback + 'The output and the connections to it are correct. '
                # print('feedback: ' + feedback)

                answerDiagramCorrect = 'true'
                break

        teacherChildNodes = graph.data(
            "MATCH (parent:Teacher)-[:TO]->(child:Teacher) WHERE parent.key= {key} RETURN child",
            parameters={"key": teacherCurrent})

        studentChildNodes = graph.data(
            "MATCH (parent:Student)-[:TO]->(child:Student) WHERE parent.key= {key} RETURN child",
            parameters={"key": studentCurrent})

        # studentGateNodeList = studentQueue

        print('got teacher child nodes')
        print('teacher queue: ')
        print(teacherQueue)
        print('student queue: ')
        print(studentQueue)

        for teacherChild in teacherChildNodes:

            print('teacher child')
            print(teacherChild)
            print('teacher current')
            print(teacherCurrent)
            print('teacher queue')
            print(teacherQueue)
            print('student queue')
            print(studentQueue)

            # matchFound = "false"

            # get all parents of current teacher child node under analysis except the current teacher parent node
            teacherChildParents = graph.data(
                "MATCH (parent:Teacher)-[:TO]->(child:Teacher) WHERE child.key= {key} AND parent.key <> {parentKey} RETURN parent",
                parameters={"key": teacherChild['child']['key'], "parentKey": teacherCurrent})

            teacherChildParentsList = list(teacherChildParents)

            print(teacherChildParentsList)

            childlessTeacherOtherParents = []
            childHavingTeacherOtherParents = []

            for teacherChildParent in teacherChildParentsList:
                print('^^^^^^^^^^get teacherChildParentChildrenNodes')
                teacherChildParentChildrenNodes = graph.data(
                    "MATCH (parent:Teacher)-[:TO]->(child:Teacher) WHERE parent.key= {parentKey} AND child.key <> {childKey} RETURN child",
                    parameters ={"parentKey": teacherChildParent['parent']['key'], "childKey": teacherChild['child']['key']})

                print('teacherChildParent: ')
                print(teacherChildParent['parent']['key'])
                print('teacherChild: ')
                print(teacherChild['child']['key'])

                # check whether other teacher parents have other children besides current child
                if not teacherChildParentChildrenNodes:
                    childlessTeacherOtherParents.append(teacherChildParent)
                else:
                    childHavingTeacherOtherParents.append(teacherChildParent)

            # print('studentGateNodeList: ')
            # print(studentGateNodeList)
            # print(studentQueue)

            # for studGate in reversed(studentGateNodeList):
            #     print('stud node gates list for loop...')
            #     print(studGate)
            #
            #     studGateInfo = graph.data(
            #         "MATCH (node:Student) WHERE node.key= {key} RETURN node",
            #         parameters={"key": studGate})
            #
            #     print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
            #     print(studGateInfo)
            #     print(currentTeacherNodeInfo[0]['node']['symbol'])
            #     print(studGateInfo[0]['node']['symbol'])
            #
            #     # think and CHANGE ordering of the inputs in the beginning if more suitable
            #     if currentTeacherNodeInfo[0]['node']['symbol'] == "input" and studGateInfo[0]['node']['symbol'] == "input":
            #         print(currentTeacherNodeInfo[0]['node']['text'])
            #         print(studGateInfo[0]['node']['text'])
            #         if not currentTeacherNodeInfo[0]['node']['text'] == studGateInfo[0]['node']['text']:
            #             continue
            #
            #     studentChildNodes = graph.data(
            #         "MATCH (parent:Student)-[:TO]->(child:Student) WHERE parent.key= {key} RETURN child",
            #         parameters={"key": studGate})
            #
            #     # noOfChildrenAnalyzed = 0

            for studentChild in studentChildNodes:
                print('stud node gate child nodes for loop...')

                if currentTeacherNodeInfo[0]['node']['symbol'] == currentStudentNodeInfo[0]['node']['symbol'] and \
                        teacherChild['child']['symbol'] == studentChild['child']['symbol']:

                    # noOfChildrenAnalyzed = noOfChildrenAnalyzed + 1

                    print('teacher node: ')
                    print(teacherChild['child']['symbol'])
                    print('child node: ')
                    print(studentChild['child']['symbol'])

                    print('teacher node: ')
                    print(teacherChild['child']['key'])
                    print('child node: ')
                    print(studentChild['child']['key'])

                    studentChildParents = graph.data(
                        "MATCH (parent:Student)-[:TO]->(child:Student) WHERE child.key= {key} AND parent.key <> {parentKey} RETURN parent",
                        parameters={"key": studentChild['child']['key'], "parentKey": studentCurrent})

                    studentChildParentsList = list(studentChildParents)

                    childlessStudentOtherParents = []
                    childHavingStudentOtherParents = []

                    for studentChildParent in studentChildParentsList:
                        print('^^^^^^^^^^get student ChildParentChildrenNodes')
                        studentChildParentChildrenNodes = graph.data(
                            "MATCH (parent:Student)-[:TO]->(child:Student) WHERE parent.key= {parentKey} AND child.key <> {childKey} RETURN child",
                            parameters={"parentKey": studentChildParent['parent']['key'],
                                        "childKey": studentChild['child']['key']})

                        print('studentChildParent: ')
                        print(studentChildParent['parent']['key'])
                        print('studentChild: ')
                        print(studentChild['child']['key'])

                        # check whether other student parents have other children besides current child
                        if not studentChildParentChildrenNodes:
                            childlessStudentOtherParents.append(studentChildParent)
                        else:
                            childHavingStudentOtherParents.append(studentChildParent)

                    print(childlessTeacherOtherParents)
                    print(childlessStudentOtherParents)

                    print(childHavingTeacherOtherParents)
                    print(childHavingStudentOtherParents)

                    if len(childlessTeacherOtherParents) == len(childlessStudentOtherParents) and \
                            len(childHavingTeacherOtherParents) == len(childHavingStudentOtherParents):
                        # print(studentChild['child']['key'])
                        # print(studentQueue)

                        # traversedChildMatchFoundNodes.append(studentCurrent)
                        #
                        # print('^^^^^^^^^^^^^^^^^Traversed child match: ')
                        # print(traversedChildMatchFoundNodes)

                        # if only current parent has one child(which is already examined by this point) or if
                        # all children of current parent has been checked and matched
                        # if len(studentChildNodes) == 1 or traversedChildMatchFoundNodes.count(studentCurrent) == len(studentChildNodes):   # noOfChildrenAnalyzed == len(studentChildNodes)
                        #     print('current node student under analysis removed from queue')
                        #     print(traversedChildMatchFoundNodes.count(studentCurrent))
                        #     print(len(studentChildNodes))
                        #     print(studentCurrent)
                        #     studentQueue.remove(studentCurrent)

                        if currentStudentNodeInfo[0]['node']['symbol'] == "input" and not currentStudentNodeInfo[0]['node']['key'] in matchedCompletedStudentNodes:
                            matchedCompletedTeacherNodes.append(teacherCurrent)
                            matchedCompletedStudentNodes.append(studentCurrent)


                        childlessStudentOtherParentsNotInQueue = []

                        # if this gate has been visited once, then already childless other parents have been removed if they were in the queue
                        # so no need to do it again and it cannot be done
                        if not studentChild['child']['key'] in visitedStudentNodes:
                            # remove childless other teacher parents and remove childless other student parents
                            for childlessTeacherNode in childlessTeacherOtherParents:
                                print('Childless Teacher node: ')
                                print(childlessTeacherNode['parent']['key'])

                                for childlessStudentNode in childlessStudentOtherParents:
                                        if childlessTeacherNode['parent']['symbol'] == childlessStudentNode['parent']['symbol']:
                                            print('Childless Student node: ')
                                            print(childlessStudentNode['parent']['key'])
                                            print(teacherQueue)
                                            print(studentQueue)

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


                        # studentGateNodeList = studentQueue

                        visitedStudentNodes.append(studentChild['child']['key'])

                        print('^^^^^^^^^^^^VISITED NODES: ')
                        print(visitedStudentNodes)

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

                        # matchFound = "true"

                        print('^^^^^^^^^^^^^matched student nodes: ')
                        print(matchedCompletedStudentNodes)

                        print('teacher queue after last node insertion to queue: ')
                        print(teacherQueue)
                        print('student queue after last node insertion to queue: ')
                        print(studentQueue)

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

            # if matchFound == "true":
            #     break

        print('teacherChildNodes list length')
        print(teacherChildNodes)
        print('studentChildNodes list length')
        print(studentChildNodes)

        if len(teacherChildNodes) == len(studentChildNodes):
            print('^^^^^^^^^^^^^^Inside substituted')
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
                print('^^^^^^^^^^^^Inside additional substituted')
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

    print('BEFORE down path macthed ')
    print(matchedCompletedStudentNodes)
    print(matchedCompletedTeacherNodes)

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
        # print(feedback)

    feedback = feedback + "Please refer your answer diagram for feedback on where you went wrong. Green " +\
               "indicates correct gates and connections while Red indicates wrong gates and connections. " +\
               "Please note that any input(to a gate) connected to a wrong gate(a gate wbich has wrong " +\
               "connections even if the symbol is the same) is identified wrong by the system and in the highlighted gate feedback. "
    print(feedback)

    print(totNoOfAdditionalNodes)
    print(totNoOfDeletedNodes)
    print(totNoOfSubstitutedNodes)
    print(totNoOfOtherIncorrectNodes)

    print('AFTER down path macthed ')
    print(matchedCompletedStudentNodes)
    print(matchedCompletedTeacherNodes)

    return matchedCompletedStudentNodes,  totNoOfAdditionalNodes, totNoOfDeletedNodes, \
           totNoOfSubstitutedNodes, totNoOfOtherIncorrectNodes, feedback, answerDiagramCorrect


# markStudBFSLogicGateAnswer()


def markLogicGateAnswer(logicGateQuestionId, studentAnswerId, isExactMatch, noOfInputs):
    if isExactMatch == "true":  # resultSet[0]
        print('true')
        matchedCompletedStudentNodes, noOfAdditionalNodes, noOfDeletedNodes, noOfSubstitutedNodes, totNoOfOtherIncorrectNodes, \
        feedback, answerDiagramCorrect = markStudBFSLogicGateAnswer()
        allocateMarksToLogicGateAnswerAndSaveToDatabase(matchedCompletedStudentNodes, len(matchedCompletedStudentNodes), \
                                                        noOfAdditionalNodes, noOfDeletedNodes, \
                                                        noOfSubstitutedNodes, totNoOfOtherIncorrectNodes, feedback, \
                                                        logicGateQuestionId, studentAnswerId)
    elif isExactMatch == "false":
        print('false')
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


# markLogicGateAnswer("false")