from CreateGraph import createNeo4jGraph, connectToGraph
from DbConnection import connectToMySQL

import re

from FlowchartProgramExecution import ifHasOnlyOnePath

# createNeo4jGraph("Flowchart", "Teacher", 46)
# createNeo4jGraph("Flowchart", "Student", 135)

def addStepMarkDetailsToDictionary(numberPresentKey,
                                   stepMarkKey,
                                   dictionary,
                                   currentNodeInfo,
                                   studentSameActionCountInCurrent):
    if not stepMarkKey == "Student":
        if numberPresentKey in dictionary and stepMarkKey in dictionary:
            dictionary[numberPresentKey] = dictionary[numberPresentKey] + currentNodeInfo[0]['node']['numberExpected']
            dictionary[stepMarkKey] = dictionary[stepMarkKey] + currentNodeInfo[0]['node']['stepMark']
        else:
            dictionary[numberPresentKey] = currentNodeInfo[0]['node']['numberExpected']
            dictionary[stepMarkKey] = currentNodeInfo[0]['node']['stepMark']
    else:
        if numberPresentKey in dictionary:
            dictionary[numberPresentKey] = dictionary[numberPresentKey] + studentSameActionCountInCurrent
        else:
            dictionary[numberPresentKey] = studentSameActionCountInCurrent


def compareStepCounts(symbol,
                      symbolNoCountKey,
                      symbolTotMarksKey,
                      teacherStepAndMarkInfo,
                      studentStepInfo,
                      scoredStepMark,
                      totNoOfAdditionalSteps,
                      totNoOfDeletedSteps,
                      feedback,
                      differenceAllowed):
    if symbolNoCountKey in teacherStepAndMarkInfo and symbolNoCountKey in studentStepInfo:
        markPerSymbolAction = teacherStepAndMarkInfo[symbolTotMarksKey] / teacherStepAndMarkInfo[symbolNoCountKey]

        # print(symbolNoCountKey)
        # print(teacherStepAndMarkInfo[symbolNoCountKey])
        # print(studentStepInfo[symbolNoCountKey])

        if not teacherStepAndMarkInfo[symbolNoCountKey] == studentStepInfo[symbolNoCountKey]:
            if teacherStepAndMarkInfo[symbolNoCountKey] > studentStepInfo[symbolNoCountKey]:
                scoredStepMark = scoredStepMark + (studentStepInfo[symbolNoCountKey] * markPerSymbolAction)

                diff = (teacherStepAndMarkInfo[symbolNoCountKey] - studentStepInfo[symbolNoCountKey])
                totNoOfDeletedSteps = totNoOfDeletedSteps + diff
                feedback = feedback + str(diff) + " " + symbol + '(s/es) is/are missing before End node. '
            elif teacherStepAndMarkInfo[symbolNoCountKey] < studentStepInfo[symbolNoCountKey]:
                scoredStepMark = scoredStepMark + (teacherStepAndMarkInfo[symbolNoCountKey] * markPerSymbolAction)

                diff = (studentStepInfo[symbolNoCountKey] - teacherStepAndMarkInfo[symbolNoCountKey])
                # a small difference is allowed
                if diff > differenceAllowed:
                    totNoOfAdditionalSteps = totNoOfAdditionalSteps + diff
                    feedback = feedback + 'There are about ' + str(diff) + ' additional ' + symbol + '(s/es) before End node. '
        else:
            scoredStepMark = scoredStepMark + (studentStepInfo[symbolNoCountKey] * markPerSymbolAction)

    elif symbolNoCountKey in teacherStepAndMarkInfo and not symbolNoCountKey in studentStepInfo:
        totNoOfDeletedSteps = totNoOfDeletedSteps + teacherStepAndMarkInfo[symbolNoCountKey]
        feedback = feedback + str(teacherStepAndMarkInfo[symbolNoCountKey]) + " " + symbol + '(s/es) is/are missing before End node. '

    elif not symbolNoCountKey in teacherStepAndMarkInfo and symbolNoCountKey in studentStepInfo:
        totNoOfAdditionalSteps = totNoOfAdditionalSteps + studentStepInfo[symbolNoCountKey]
        feedback = feedback + 'There are ' + str(studentStepInfo[symbolNoCountKey]) + ' additional ' + symbol + '(s/es) before End node. '

    return scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback


def allocateMarksAndSaveToDatabase(scoredStepMark,
                                   noOfAdditionalNodes,
                                   noOfDeletedNodes,
                                   feedback,
                                   flowchartQuestionId,
                                   studentAnswerId):
    connection = connectToMySQL()
    cur = connection.cursor()
    cur.execute("SELECT sequenceMark FROM flowchart_question WHERE flowchartqId = %s", (flowchartQuestionId))
    resultSet = cur.fetchone()
    print('starting mark allocation...')

    # stepMark = resultSet[0]
    sequenceMark = resultSet[0]

    sequenceMarkForAddDeleteDeductions = (70/100) * sequenceMark

    totalAddDeleteDiff = noOfAdditionalNodes + noOfDeletedNodes

    if scoredStepMark == 0:
        scoredSequenceMark = 0
    else:
        # maximum number of errors for additions and deletions that are allowed is 5
        if totalAddDeleteDiff <= 5:
            scoredSequenceMark = sequenceMark - (totalAddDeleteDiff/5) * sequenceMarkForAddDeleteDeductions
        else:
            scoredSequenceMark = sequenceMark - sequenceMarkForAddDeleteDeductions

    scoredFullMark = scoredStepMark + scoredSequenceMark

    print(scoredStepMark)
    print(scoredSequenceMark)
    print(noOfAdditionalNodes)
    print(noOfDeletedNodes)

    cur.execute("UPDATE flowchart_stud_answer SET stepMark = %s, sequenceMark = %s WHERE flowchartStudAnsId = %s",
                (scoredStepMark, scoredSequenceMark, studentAnswerId))

    cur.execute("UPDATE student_answer SET scoredMark = %s, feedback = %s, markedStatus = %s WHERE studAnswerId = %s",
                (scoredFullMark, feedback, "true", studentAnswerId))
    cur.close()
    connection.close()


def callStepCountingForAllSymbols(teacherStepAndMarkInfo,
                                  studentStepInfo,
                                  scoredStepMark,
                                  totNoOfAdditionalSteps,
                                  totNoOfDeletedSteps,
                                  feedback):
    scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = compareStepCounts('Input',
                                                                                              'noOfInputs',
                                                                                              'totInputMarks',
                                                                                              teacherStepAndMarkInfo,
                                                                                              studentStepInfo,
                                                                                              scoredStepMark,
                                                                                              totNoOfAdditionalSteps,
                                                                                              totNoOfDeletedSteps,
                                                                                              feedback,
                                                                                              0)

    scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = compareStepCounts('Process',
                                                                                              'noOfProcesses',
                                                                                              'totProcessMarks',
                                                                                              teacherStepAndMarkInfo,
                                                                                              studentStepInfo,
                                                                                              scoredStepMark,
                                                                                              totNoOfAdditionalSteps,
                                                                                              totNoOfDeletedSteps,
                                                                                              feedback,
                                                                                              4)

    scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = compareStepCounts('Output',
                                                                                              'noOfOutputs',
                                                                                              'totOutputMarks',
                                                                                              teacherStepAndMarkInfo,
                                                                                              studentStepInfo,
                                                                                              scoredStepMark,
                                                                                              totNoOfAdditionalSteps,
                                                                                              totNoOfDeletedSteps,
                                                                                              feedback,
                                                                                              0)

    scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = compareStepCounts('Decision',
                                                                                              'noOfDecisions',
                                                                                              'totDecisionMarks',
                                                                                              teacherStepAndMarkInfo,
                                                                                              studentStepInfo,
                                                                                              scoredStepMark,
                                                                                              totNoOfAdditionalSteps,
                                                                                              totNoOfDeletedSteps,
                                                                                              feedback,
                                                                                              2)

    return scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback


# def ifHasOnlyOnePath(graph,
#                      stack,
#                      stackAppendNode,
#                      traversedNodes,
#                      traversedCommonNodesAppendNode,
#                      commonNodes,
#                      currentNode,
#                      ifNodes,
#                      ifDictionary):
#     stack.append(stackAppendNode)
#
#     traversedNodes.append(traversedCommonNodesAppendNode)
#
#     commonNodes.append(traversedCommonNodesAppendNode)
#
#     if not currentNode in ifNodes:
#         ifNodes.append(currentNode)
#
#     noOfPathsToCommonNode = graph.data("MATCH (parent:Student)-[:TO|YES|NO]->(child:Student) WHERE child.key= {key} "
#                                        "RETURN parent", parameters={"key": traversedCommonNodesAppendNode})
#     if not currentNode in ifDictionary:
#         ifDictionary[currentNode] = len(noOfPathsToCommonNode)


def traverseStepsAndHandleDetails(caller,
                                  graph,
                                  stack,
                                  traversedNodes,
                                  stepDetailsDictionary,
                                  visitedNodes,
                                  lastNode,
                                  previousNode,
                                  commonNodes,
                                  ifNodes,
                                  ifDictionary,
                                  mainIfCompletedNoOfPaths,
                                  studIfElseStepInfoDictList):
    while True:
        currentNode = stack.pop()

        traversedNodes.append(currentNode)

        continueWithFlow = 'false'

        if not commonNodes:
            continueWithFlow = 'true'

        while commonNodes:
            currentCommonNode = commonNodes.pop()

            if currentNode == currentCommonNode:
                currentIfKey = ifNodes.pop()

                if traversedNodes.count(currentNode) < ifDictionary.get(currentIfKey, "none"):
                    commonNodes.append(currentCommonNode)
                    ifNodes.append(currentIfKey)
                    break
                elif traversedNodes.count(currentNode) == ifDictionary.get(currentIfKey, "none"):
                    # continueWithFlow = 'true'
                    # continue
                    stack.append(currentNode)
                    lastNode = "CommonNode"
                    return lastNode, previousNode, ifNodes, ifDictionary
            else:
                continueWithFlow = 'true'
                commonNodes.append(currentCommonNode)
                break

        if not commonNodes:
            ifDictionary = {}
            ifNodes = []
            mainIfCompletedNoOfPaths = 0

        if continueWithFlow == "true":
            currentNodeInfo = graph.data("MATCH (node:" + caller + ") WHERE node.key= {key} RETURN node",
                                            parameters={"key": currentNode})

            if not currentNodeInfo[0]['node']['symbol'] == "Start":
                currentNodeOtherParents = graph.data("MATCH (parent:" + caller + ")-[:TO|YES|NO]->(child:" + caller + ") WHERE "
                                                        "child.key= {childKey} and parent.key <> {prevParentKey} RETURN parent",
                                                        parameters={"childKey": currentNode,
                                                                    "prevParentKey": previousNode})

                if not currentNodeOtherParents:
                    if currentNodeInfo[0]['node']['symbol'] == "End":
                        break

                    if caller == "Teacher":
                        if currentNodeInfo[0]['node']['numberExpected'] and currentNodeInfo[0]['node']['stepMark']:
                            if currentNodeInfo[0]['node']['symbol'] == "Input":
                                addStepMarkDetailsToDictionary('noOfInputs', 'totInputMarks', stepDetailsDictionary,
                                                               currentNodeInfo, 0)
                            elif currentNodeInfo[0]['node']['symbol'] == "Process":
                                addStepMarkDetailsToDictionary('noOfProcesses', 'totProcessMarks', stepDetailsDictionary,
                                                               currentNodeInfo, 0)
                            elif currentNodeInfo[0]['node']['symbol'] == "Output":
                                addStepMarkDetailsToDictionary('noOfOutputs', 'totOutputMarks', stepDetailsDictionary,
                                                               currentNodeInfo, 0)
                    elif caller == "Student":
                        currentNodeText = currentNodeInfo[0]['node']['text']

                        noOfSameInCurrentNode = 0

                        if currentNodeInfo[0]['node']['symbol'] == "Input":
                            if '\'' in currentNodeText:
                                words = re.split("[,]+", currentNodeText)
                            else:
                                words = re.split("[, ]+", currentNodeText)

                            for word in words:
                                if not (re.match("input", word, re.IGNORECASE) or re.match("enter", word, re.IGNORECASE) or
                                        re.match("read", word, re.IGNORECASE) or '\'' in word or not word):
                                    noOfSameInCurrentNode = noOfSameInCurrentNode + 1

                            addStepMarkDetailsToDictionary('noOfInputs', 'Student', stepDetailsDictionary, currentNodeInfo,
                                                           noOfSameInCurrentNode)
                        elif currentNodeInfo[0]['node']['symbol'] == "Process":
                            addStepMarkDetailsToDictionary('noOfProcesses', 'Student', stepDetailsDictionary, currentNodeInfo,
                                                           1)
                        elif currentNodeInfo[0]['node']['symbol'] == "Output":
                            if '+' in currentNodeText and '\'' in currentNodeText:
                                words = re.split("[+,]+", currentNodeText)
                            elif ',' in currentNodeText and '\'' in currentNodeText and not '+' in currentNodeText:
                                words = re.split("[,]+", currentNodeText)
                            elif '\'' in currentNodeText and not (',' in currentNodeText or '+' in currentNodeText):
                                words = re.split("[']+", currentNodeText)
                            else:
                                words = re.split("[, ]+", currentNodeText)

                            for wordSet in words:
                                if not (re.search("output", wordSet, re.IGNORECASE) or re.search("display", wordSet,
                                                                                                 re.IGNORECASE) or re.search(
                                    "print", wordSet, re.IGNORECASE) or '\'' in wordSet or
                                        not wordSet):
                                    noOfSameInCurrentNode = noOfSameInCurrentNode + 1

                            addStepMarkDetailsToDictionary('noOfOutputs', 'Student', stepDetailsDictionary, currentNodeInfo,
                                                           noOfSameInCurrentNode)

                    if not currentNodeInfo[0]['node']['symbol'] == "Decision":
                        visitedNodes.append(currentNode)

                if currentNodeInfo[0]['node']['symbol'] == "End":
                    break

                if currentNodeInfo[0]['node']['symbol'] == "Decision":
                    if traversedNodes.count(currentNode) == 1:
                        if caller == "Teacher" and currentNodeInfo[0]['node']['numberExpected'] and currentNodeInfo[0]['node']['stepMark']:
                            addStepMarkDetailsToDictionary('noOfDecisions', 'totDecisionMarks', stepDetailsDictionary,
                                                           currentNodeInfo, 0)
                        elif caller == "Student":
                            addStepMarkDetailsToDictionary('noOfDecisions', 'Student', stepDetailsDictionary,
                                                           currentNodeInfo, 1)

                    yesCurrentChildNode = graph.data(
                        "MATCH (parent:" + caller + ")-[:YES]->(child:" + caller + ") WHERE parent.key= {key} RETURN child",
                        parameters={"key": currentNode})

                    yesChildParents = graph.data(
                        "MATCH (parent:" + caller + ")-[]->(child:" + caller + ") WHERE child.key= {key} RETURN parent",
                        parameters={"key": yesCurrentChildNode[0]['child']['key']})

                    noCurrentChildNode = graph.data(
                        "MATCH (parent:" + caller + ")-[:NO]->(child:" + caller + ") WHERE parent.key= {key} RETURN child",
                        parameters={"key": currentNode})

                    noChildParents = graph.data(
                        "MATCH (parent:" + caller + ")-[]->(child:" + caller + ") WHERE child.key= {key} RETURN parent",
                        parameters={"key": noCurrentChildNode[0]['child']['key']})

                    doWhileFound = "false"

                    if (yesCurrentChildNode[0]['child']['key'] in traversedNodes or
                            noCurrentChildNode[0]['child']['key'] in traversedNodes):

                        doWhileFound = "true"

                        currentStructure = "DoWhile"

                        if yesCurrentChildNode[0]['child']['key'] in traversedNodes:
                            if traversedNodes.count(currentNode) == 1:
                                stack.append(yesCurrentChildNode[0]['child']['key'])
                            elif traversedNodes.count(currentNode) > 1:
                                stack.append(noCurrentChildNode[0]['child']['key'])
                        elif noCurrentChildNode[0]['child']['key'] in traversedNodes:
                            if traversedNodes.count(currentNode) == 1:
                                stack.append(noCurrentChildNode[0]['child']['key'])
                            elif traversedNodes.count(currentNode) > 1:
                                stack.append(yesCurrentChildNode[0]['child']['key'])
                    else:
                        # if (len(whileNodes) == 0 and traversedNodes.count(currentNode) == 1) or \
                        #         (len(whileNodes) == 1 and traversedNodes.count(currentNode) == 2):
                        if traversedNodes.count(currentNode) == 1 or traversedNodes.count(currentNode) == 2:
                            loopPath = graph.data("MATCH (currentNode:" + caller + ")-[r:YES|NO]->(nextNode:" + caller +
                                                  ")-[*]->(currentNode:" + caller + ") WHERE currentNode.key = "
                                                  "{currentNodeKey} RETURN DISTINCT TYPE(r)",
                                                  parameters={"currentNodeKey": currentNode})
                        # elif (len(whileNodes) == 1 and traversedNodes.count(currentNode) == 1) or \
                        #         (len(whileNodes) == 2 and traversedNodes.count(currentNode) == 2):
                        #     loopPath = graph.data(
                        #         "MATCH path = (currentNode:Student)-[r:YES|NO]->(nextNode:Student)-[*]->"
                        #         "(currentNode:Student) WHERE currentNode.key = {currentNodeKey} "
                        #         "WITH path, r MATCH (previousIfNode: Student) WHERE previousIfNode.key = "
                        #         "{previousIfNodeKey} AND NOT previousIfNode IN NODES(path) RETURN TYPE(r)",
                        #         parameters={"currentNodeKey": currentNode, "previousIfNodeKey": whileNodes[0]})

                        if not loopPath:
                            if doWhileFound == "false":
                                ifFound = "false"

                                currentCommonNode = graph.data(
                                    "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(a:" + caller + ")-[*]->(commonNode:" +
                                    caller + "), path2 = (currentDecision:" + caller + ")-[:NO]->(b:" + caller + ")-[*]->"
                                    "(commonNode:" + caller + ") WHERE currentDecision.key={currentNodeKey} and path1 <> path2 "
                                    "RETURN DISTINCT commonNode",
                                    parameters={"currentNodeKey": currentNode})

                                if len(noChildParents) > 1 and traversedNodes.count(currentNode) == 1:
                                    if not currentCommonNode:
                                        currentCommonNode = graph.data(
                                            "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(a:" + caller + ")-[*]->"
                                            "(commonNode:" + caller + "), path2 = (currentDecision:" + caller + ")-[:NO]->"
                                            "(commonNode:" + caller + ") WHERE currentDecision.key={currentNodeKey} and "
                                            "path1 <> path2 RETURN DISTINCT commonNode",
                                            parameters={"currentNodeKey": currentNode})

                                    if noCurrentChildNode[0]['child']['key'] == currentCommonNode[0]['commonNode']['key']:
                                        ifFound = "true"
                                        currentStructure = "If"
                                        # stack.append(yesCurrentChildNode[0]['child']['key'])
                                        ifHasOnlyOnePath(graph, stack, yesCurrentChildNode[0]['child']['key'],
                                                         traversedNodes, noCurrentChildNode[0]['child']['key'], commonNodes,
                                                         currentNode, ifNodes, ifDictionary)
                                elif len(yesChildParents) > 1 and traversedNodes.count(currentNode) == 1:
                                    if not currentCommonNode:
                                        currentCommonNode = graph.data(
                                            "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(commonNode:" + caller + "), "
                                            "path2 = (currentDecision:" + caller + ")-[:NO]->(b:" + caller + ")-[*]->(commonNode:" +
                                            caller + ") WHERE currentDecision.key={currentNodeKey} and path1 <> path2 RETURN "
                                                     "DISTINCT commonNode", parameters={"currentNodeKey": currentNode})

                                    if yesCurrentChildNode[0]['child']['key'] == currentCommonNode[0]['commonNode']['key']:
                                        ifFound = "true"
                                        currentStructure = "IfNot"
                                        # stack.append(noCurrentChildNode[0]['child']['key'])
                                        ifHasOnlyOnePath(graph, stack, noCurrentChildNode[0]['child']['key'], traversedNodes,
                                                         yesCurrentChildNode[0]['child']['key'], commonNodes, currentNode,
                                                         ifNodes, ifDictionary)

                                if ifFound == "false":
                                    if noCurrentChildNode[0]['child']['symbol'] == "Decision":
                                        currentStructure = "IfElseIf"
                                    else:
                                        currentStructure = "IfElse"

                                    if not currentNode in ifNodes:
                                        commonNodes.append(currentCommonNode[0]['commonNode']['key'])
                                        ifNodes.append(currentNode)

                                    noOfPathsToCommonNode = graph.data(
                                        "MATCH (parent:Student)-[:TO|YES|NO]->(child:Student) WHERE "
                                        "child.key= {key} RETURN parent",
                                        parameters={"key": currentCommonNode[0]['commonNode']['key']})

                                    if yesCurrentChildNode[0]['child']['key'] in visitedNodes:
                                        stack.append(noCurrentChildNode[0]['child']['key'])

                                        visitedNodes.append(currentNode)

                                        if currentNode == ifNodes[0]:
                                            completedNoOfPaths = graph.data("MATCH paths = (currentDecision:Student)-[:YES]->"
                                                                            "(a:Student)-[*]->(commonNode:Student) WHERE currentDecision.key={currentNodeKey} and "
                                                                            "commonNode.key={commonNodeKey}  RETURN count(paths)",
                                                                            parameters={"currentNodeKey":
                                                                                            currentNode, "commonNodeKey":
                                                                                            currentCommonNode[0]['commonNode'][
                                                                                                'key']})

                                            mainIfCompletedNoOfPaths = completedNoOfPaths[0]['count(paths)']
                                    else:
                                        stack.append(currentNode)
                                        stack.append(yesCurrentChildNode[0]['child']['key'])

                                        # no need to do again in no path, as key will be added here in the yes path, so it will anyway be there in the dictionary
                                        if not ifNodes[0] in visitedNodes:
                                            if not currentNode in ifDictionary:
                                                # ifDictionary[currentNode] = noOfPathsToCommonNode[0]['count(paths)']
                                                ifDictionary[currentNode] = len(noOfPathsToCommonNode)
                                        else:
                                            if not currentNode in ifDictionary:
                                                # ifDictionary[currentNode] = mainIfCompletedNoOfPaths + noOfPathsToCommonNode[0]['count(paths)']
                                                ifDictionary[currentNode] = mainIfCompletedNoOfPaths + len(
                                                    noOfPathsToCommonNode)

                        elif loopPath[0]['TYPE(r)'] == "YES":
                            currentStructure = "While"
                            if traversedNodes.count(currentNode) == 1:
                                stack.append(yesCurrentChildNode[0]['child']['key'])
                            elif traversedNodes.count(currentNode) > 1:
                                stack.append(noCurrentChildNode[0]['child']['key'])
                        elif loopPath[0]['TYPE(r)'] == "NO":
                            currentStructure = "While"
                            if traversedNodes.count(currentNode) == 1:
                                stack.append(noCurrentChildNode[0]['child']['key'])
                            elif traversedNodes.count(currentNode) > 1:
                                stack.append(yesCurrentChildNode[0]['child']['key'])

                    if not (caller == "Student" and currentStructure == "IfElse" and traversedNodes.count(currentNode) > 1):
                        lastNode = "Decision"
                        # lastNode = currentStructure
                        previousNode = currentNode
                        break
                    else:
                        studIfElseStepInfoDictList.append(stepDetailsDictionary)
                        stepDetailsDictionary.clear()

            if not currentNodeInfo[0]['node']['symbol'] == "Decision":
                curChildNode = graph.data(
                    "MATCH (parent:" + caller + ")-[:TO]->(child:" + caller + ") WHERE parent.key= {key} RETURN child",
                    parameters={"key": currentNode})

                stack.append(curChildNode[0]['child']['key'])

            previousNode = currentNode

    return lastNode, previousNode, ifNodes, ifDictionary


def markStudDFSFlowchartAnswer():
    # Connect to Graph
    graph = connectToGraph()

    teacherStartNodeKey = graph.data(
        "MATCH (node:Teacher) WHERE node.symbol='Start' RETURN node.key")
    studentStartNodeKey = graph.data(
        "MATCH (node:Student) WHERE node.symbol='Start' RETURN node.key")

    teacherStack = [teacherStartNodeKey[0]['node.key']]
    studentStack = [studentStartNodeKey[0]['node.key']]

    teachVisitedNodes = []
    studVisitedNodes = []

    teacherStepAndMarkInfo = {}
    studentStepInfo = {}

    teachIfElseStepInfoDictList = []
    studIfElseStepInfoDictList = []

    nestedStructuresDictList = []

    teacherTraversedNodes = []
    studentTraversedNodes = []

    # maintains common nodes in paths for all if structures
    teachCommonNodes = []
    # maintains if node keys for if-else structures
    teachIfNodes = []
    # this dictionary has keys which are the node keys of ifs under analysis until main if path is joined and values are
    # an indication of the number of times the path joining node must be visited to continue. Yes path will have it
    # corresponding values because yes is analyzed first while no path will have the summation of yes completed ones
    # and the corresponding no path ifs, yes has already been traversed, and that many
    # has to be traversed by the time of no path ending.
    teachIfDictionary = {}
    teachMainIfCompletedNoOfPaths = 0

    studCommonNodes = []
    studIfNodes = []
    studIfDictionary = {}
    studMainIfCompletedNoOfPaths = 0

    teachPrevNode = -99
    studPrevNode = -99

    scoredStepMark = 0
    totNoOfAdditionalSteps = 0
    totNoOfDeletedSteps = 0

    feedback = ""

    markingFinished = "false"

    while markingFinished == "false":
        # endOrDecisionFound = "false"

        teacherLastNode = "End"
        studentLastNode = "End"

        teacherLastNode, teachPrevNode, teachIfNodes, teachIfDictionary = traverseStepsAndHandleDetails('Teacher', graph,
                                                        teacherStack, teacherTraversedNodes,
                                                        teacherStepAndMarkInfo, teachVisitedNodes, teacherLastNode,
                                                        teachPrevNode, teachCommonNodes, teachIfNodes, teachIfDictionary,
                                                        teachMainIfCompletedNoOfPaths, teachIfElseStepInfoDictList)

        studentLastNode, studPrevNode, studIfNodes, studIfDictionary = traverseStepsAndHandleDetails('Student', graph,
                                                        studentStack, studentTraversedNodes,
                                                        studentStepInfo, studVisitedNodes, studentLastNode, studPrevNode,
                                                        studCommonNodes, studIfNodes, studIfDictionary,
                                                        studMainIfCompletedNoOfPaths, studIfElseStepInfoDictList)

        print(studIfElseStepInfoDictList)

        if teacherLastNode == "End" and studentLastNode == "End":
            scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = \
                callStepCountingForAllSymbols(teacherStepAndMarkInfo, studentStepInfo, scoredStepMark,
                                              totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback)

            if totNoOfAdditionalSteps == 0 and totNoOfDeletedSteps == 0:
                feedback = feedback + 'All the steps are correct. Well Done!'
            else:
                feedback = feedback + 'Please refer teacher\'s answer diagram to identify the additional and deleted nodes indicated in the feedback. '

            print(feedback)

            allocateMarksAndSaveToDatabase(scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback,
                                        #   flowchartQuestionId, studentAnswerId)
                                           46, 135)

            markingFinished = "true"

        elif teacherLastNode == "Decision" and studentLastNode == "Decision":
        # elif ((teacherLastNode == "If" or teacherLastNode == "IfNot") and (studentLastNode == "If" or
        #         studentLastNode == "IfNot")) or ((teacherLastNode == "While" or teacherLastNode == "DoWhile") and
        #         (studentLastNode == "While" or studentLastNode == "DoWhile")):
            scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = \
                callStepCountingForAllSymbols(teacherStepAndMarkInfo, studentStepInfo, scoredStepMark,
                                              totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback)

            teacherStepAndMarkInfo.clear()
            studentStepInfo.clear()
        elif teacherLastNode == "Decision" and studentLastNode == "CommonNode":


            teacherStepAndMarkInfo.clear()

markStudDFSFlowchartAnswer()
