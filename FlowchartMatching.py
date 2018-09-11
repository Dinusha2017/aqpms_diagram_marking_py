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

    print('Scored Step Mark: ' + str(scoredStepMark))
    print('Scored Sequence Mark: ' + str(scoredSequenceMark))
    print('Number of Additional Nodes Found: ' + str(noOfAdditionalNodes))
    print('Number of Deleted Nodes: ' + str(noOfDeletedNodes))
    print('Feedback: ' + str(feedback))

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
                                                                                              0)   # 2

    return scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback

# def callStepCountForAllPossibilities(teacherStepAndMarkInfo,
#                                      studIfElseStepInfoDictList,
#                                      scoredStepMark,
#                                      totNoOfAdditionalSteps,
#                                      totNoOfDeletedSteps,
#                                      feedback):
#
#     stepScore = 0
#     maxScore = stepScore
#     additionalSteps=0
#     maxAddSteps = 0
#     deletedSteps = 0
#     maxDelSteps = 0
#     currentFeedback = ""
#     maxFeedback = ""
#
#     maxElementIndex = -99
#
#     count = 0
#
#     while count < len(studIfElseStepInfoDictList):
#         stepScore, additionalSteps, deletedSteps, currentFeedback = compareStepCounts('Input',
#                                                                                       'noOfInputs',
#                                                                                       'totInputMarks',
#                                                                                       teacherStepAndMarkInfo,
#                                                                                       studIfElseStepInfoDictList[count],
#                                                                                       stepScore,
#                                                                                       additionalSteps,
#                                                                                       deletedSteps,
#                                                                                       currentFeedback,
#                                                                                       0)
#
#         stepScore, additionalSteps, deletedSteps, currentFeedback = compareStepCounts('Process',
#                                                                                       'noOfProcesses',
#                                                                                       'totProcessMarks',
#                                                                                       teacherStepAndMarkInfo,
#                                                                                       studIfElseStepInfoDictList[count],
#                                                                                       stepScore,
#                                                                                       additionalSteps,
#                                                                                       deletedSteps,
#                                                                                       currentFeedback,
#                                                                                       4)
#
#         stepScore, additionalSteps, deletedSteps, currentFeedback = compareStepCounts('Output',
#                                                                                       'noOfOutputs',
#                                                                                       'totOutputMarks',
#                                                                                       teacherStepAndMarkInfo,
#                                                                                       studIfElseStepInfoDictList[count],
#                                                                                       stepScore,
#                                                                                       additionalSteps,
#                                                                                       deletedSteps,
#                                                                                       currentFeedback,
#                                                                                       0)
#
#         stepScore, additionalSteps, deletedSteps, currentFeedback = compareStepCounts('Decision',
#                                                                                       'noOfDecisions',
#                                                                                       'totDecisionMarks',
#                                                                                       teacherStepAndMarkInfo,
#                                                                                       studIfElseStepInfoDictList[count],
#                                                                                       stepScore,
#                                                                                       additionalSteps,
#                                                                                       deletedSteps,
#                                                                                       currentFeedback,
#                                                                                       0)
#
#         if stepScore > maxScore:
#             maxScore = stepScore
#             maxAddSteps = additionalSteps
#             maxDelSteps = deletedSteps
#             maxFeedback = currentFeedback
#             maxElementIndex = count
#
#         stepScore = 0
#         additionalSteps = 0
#         deletedSteps = 0
#         currentFeedback = ""
#
#         count = count + 1
#
#     scoredStepMark = scoredStepMark + maxScore
#     totNoOfAdditionalSteps = totNoOfAdditionalSteps + maxAddSteps
#     totNoOfDeletedSteps = totNoOfDeletedSteps + maxDelSteps
#     feedback = feedback + maxFeedback
#
#     del studIfElseStepInfoDictList[maxElementIndex]
#
#     return scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback

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


def getAllIncorrectNodes(caller,
                         graph,
                         stack,
                         totNoOfIncorrectSteps,
                         feedback,
                         traversedNodes,
                         visitedNodes):
    noOfIncorrectNodes = 0
    print(stack)
    while stack:
        currentNode = stack.pop()

        if caller == "Teacher" or caller == "Student":
            currentNodeInfo = graph.data("MATCH (node:" + caller + ") WHERE node.key= {key} RETURN node",
                                         parameters={"key": currentNode})
        else:
            currentNodeInfo = graph.data("MATCH (node:Teacher) WHERE node.key= {key} RETURN node",
                                         parameters={"key": currentNode})

        if not (currentNodeInfo[0]['node']['symbol'] == "End") and not (currentNode in traversedNodes):
            print(currentNode)
            totNoOfIncorrectSteps = totNoOfIncorrectSteps + 1
            noOfIncorrectNodes = noOfIncorrectNodes + 1

        if caller == "Teacher" or caller == "Student":
            curChildNode = graph.data(
                "MATCH (parent:" + caller + ")-[:TO|YES|NO]->(child:" + caller + ") WHERE parent.key= {key} RETURN child",
                parameters={"key": currentNode})
        else:
            curChildNode = graph.data(
                "MATCH (parent:Teacher)-[:TO|YES|NO]->(child:Teacher) WHERE parent.key= {key} RETURN child",
                parameters={"key": currentNode})

        for child in curChildNode:
            if not child['child']['key'] in visitedNodes:
                stack.append(child['child']['key'])

        visitedNodes.append(currentNode)

    if caller == "Student":
        feedback = feedback + 'There are ' + str(noOfIncorrectNodes) + ' additional nodes in the student\'s answer after the End node in teacher\'s answer. '
    elif caller == "Teacher":
        feedback = feedback + str(noOfIncorrectNodes) + ' nodes that should appear before the End node are missing in the student\'s answer. '
    elif caller == "TConditionSLoop":
        feedback = feedback + 'Incorrect Decision node: Student has added a loop instead of a condition in the outer-most level. ' + \
                   str(noOfIncorrectNodes) + ' nodes should appear after the start of the expected condition in the student\'s answer, excluding End node. '
    elif caller == "TLoopSCondition":
        feedback = feedback + 'Incorrect Decision node: Student has added a condition instead of a loop in the outer-most level. ' + \
                   str(noOfIncorrectNodes) + ' nodes should appear after the start of the expected loop in the student\'s answer, excluding End node. '

    return totNoOfIncorrectSteps, feedback


def handleIfStructureTraversal(caller,
                               graph,
                               stack,
                               currentNode,
                               noChildParents,
                               yesChildParents,
                               traversedNodes,
                               noCurrentChildNode,
                               yesCurrentChildNode,
                               currentStructure,
                               commonNodes,
                               ifNodes,
                               ifDictionary,
                               visitedNodes,
                               ifFound):
    currentCommonNode = graph.data(
        "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(a:" + caller + ")-[*]->(commonNode:" +
        caller + "), path2 = (currentDecision:" + caller + ")-[:NO]->(b:" + caller + ")-[*]->" +
        "(commonNode:" + caller + ") WHERE currentDecision.key={currentNodeKey} and path1 <> path2 " +
        "RETURN DISTINCT commonNode",
        parameters={"currentNodeKey": currentNode})

    if len(noChildParents) > 1 and traversedNodes.count(currentNode) == 1:
        if not currentCommonNode:
            currentCommonNode = graph.data(
                "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(a:" + caller + ")-[*]->" +
                "(commonNode:" + caller + "), path2 = (currentDecision:" + caller + ")-[:NO]->" +
                "(commonNode:" + caller + ") WHERE currentDecision.key={currentNodeKey} and " +
                "path1 <> path2 RETURN DISTINCT commonNode",
                parameters={"currentNodeKey": currentNode})

        if noCurrentChildNode[0]['child']['key'] == currentCommonNode[0]['commonNode']['key']:
            ifFound = "true"
            if not currentStructure:
                currentStructure = "If"
            # stack.append(yesCurrentChildNode[0]['child']['key'])
            ifHasOnlyOnePath(graph, stack, yesCurrentChildNode[0]['child']['key'],
                             traversedNodes, noCurrentChildNode[0]['child']['key'], commonNodes,
                             currentNode, ifNodes, ifDictionary)
            visitedNodes.append(currentNode)
    elif len(yesChildParents) > 1 and traversedNodes.count(currentNode) == 1:
        if not currentCommonNode:
            currentCommonNode = graph.data(
                "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(commonNode:" + caller + "), " +
                "path2 = (currentDecision:" + caller + ")-[:NO]->(b:" + caller + ")-[*]->(commonNode:" +
                caller + ") WHERE currentDecision.key={currentNodeKey} and path1 <> path2 RETURN " +
                "DISTINCT commonNode", parameters={"currentNodeKey": currentNode})

        if yesCurrentChildNode[0]['child']['key'] == currentCommonNode[0]['commonNode']['key']:
            ifFound = "true"
            if not currentStructure:
                currentStructure = "IfNot"
            # stack.append(noCurrentChildNode[0]['child']['key'])
            ifHasOnlyOnePath(graph, stack, noCurrentChildNode[0]['child']['key'], traversedNodes,
                             yesCurrentChildNode[0]['child']['key'], commonNodes, currentNode,
                             ifNodes, ifDictionary)
            visitedNodes.append(currentNode)

    if ifFound == "false":
        # if noCurrentChildNode[0]['child']['symbol'] == "Decision":
        #     curNoChildCommonNode = graph.data(
        #         "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(a:" + caller +
        #         ")-[*]->(commonNode:" + caller + "), path2 = (currentDecision:" + caller +
        #         ")-[:NO]->(b:" + caller + ")-[*]->" + "(commonNode:" + caller +
        #         ") WHERE currentDecision.key={currentNodeKey} and " +
        #         "path1 <> path2 RETURN DISTINCT commonNode",
        #         parameters={"currentNodeKey": noCurrentChildNode[0]['child']['key']})
        #
        #     if not curNoChildCommonNode:
        #         curNoChildCommonNode = graph.data(
        #             "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(a:" + caller +
        #             ")-[*]->(commonNode:" + caller + "), path2 = (currentDecision:" + caller +
        #             ")-[:NO]->""(commonNode:" + caller + ") WHERE currentDecision.key={currentNodeKey} and " +
        #             "path1 <> path2 RETURN DISTINCT commonNode",
        #             parameters={"currentNodeKey": noCurrentChildNode[0]['child']['key']})
        #
        #     if not curNoChildCommonNode:
        #         curNoChildCommonNode = graph.data(
        #             "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(commonNode:" +
        #             caller + "), path2 = (currentDecision:" + caller + ")-[:NO]->(b:" + caller +
        #             ")-[*]->(commonNode:" + caller +
        #             ") WHERE currentDecision.key={currentNodeKey} and path1 <> path2 RETURN " +
        #             "DISTINCT commonNode",
        #             parameters={"currentNodeKey": noCurrentChildNode[0]['child']['key']})
        #
        #     if curNoChildCommonNode[0]['commonNode']['key'] == currentCommonNode[0]['commonNode']['key']:
        #         if not currentStructure:
        #             currentStructure = "IfElseIf"
        #     else:
        #         if not currentStructure:
        #             currentStructure = "IfElse"
        # else:
        if not currentStructure:
            currentStructure = "IfElse"

        ifFound = "true"

        if not currentNode in ifNodes:
            commonNodes.append(currentCommonNode[0]['commonNode']['key'])
            ifNodes.append(currentNode)

        # DGAMLK fix loop parent bug
        noOfPathsToCommonNode = graph.data(
            "MATCH (parent:" + caller + ")-[:TO|YES|NO]->(child:" + caller + ") WHERE " +
            "child.key= {key} RETURN parent", parameters={"key": currentCommonNode[0]['commonNode']['key']})

        if yesCurrentChildNode[0]['child']['key'] in visitedNodes:
            stack.append(noCurrentChildNode[0]['child']['key'])

            visitedNodes.append(currentNode)

            if currentNode == ifNodes[0]:
                completedNoOfPaths = graph.data("MATCH paths = (currentDecision:" + caller + ")-[:YES]->" +
                "(a:" + caller + ")-[*]->(commonNode:" + caller + ") WHERE currentDecision.key={currentNodeKey} and " +
                "commonNode.key={commonNodeKey}  RETURN count(paths)", parameters={"currentNodeKey": currentNode,
                                                                                   "commonNodeKey":
                                                                                   currentCommonNode[0]['commonNode']['key']})

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
                    # ifDictionary[currentNode] = mainIfCompletedNoOfPaths + len(
                    #     noOfPathsToCommonNode)
                    # BUG: else if bug in marking: noOfPathsToCommonNode is correct
                    ifDictionary[currentNode] = len(noOfPathsToCommonNode)

    return currentStructure, ifFound

def handleWhileStructureTraversal(stack,
                                  loopPath,
                                  currentStructure,
                                  traversedNodes,
                                  currentNode,
                                  yesCurrentChildNode,
                                  noCurrentChildNode,
                                  whileNodes,
                                  ifNodes,
                                  ifDictionary,
                                  lastNode,
                                  previousNode):
    if loopPath[0]['TYPE(r)'] == "YES":
        if not currentStructure:
            currentStructure = "While"
        if traversedNodes.count(currentNode) == 1:
            stack.append(yesCurrentChildNode[0]['child']['key'])
            whileNodes.append(currentNode)
        elif traversedNodes.count(currentNode) > 1:
            stack.append(noCurrentChildNode[0]['child']['key'])
            currentStructure = ""
    elif loopPath[0]['TYPE(r)'] == "NO":
        if not currentStructure:
            currentStructure = "While"
        if traversedNodes.count(currentNode) == 1:
            stack.append(noCurrentChildNode[0]['child']['key'])
            whileNodes.append(currentNode)
        elif traversedNodes.count(currentNode) > 1:
            stack.append(yesCurrentChildNode[0]['child']['key'])
            currentStructure = ""

    return lastNode, previousNode, ifNodes, ifDictionary, currentStructure


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
                                  doWhileNodes,
                                  whileNodes,
                                  nestedLevel):
    isDoWhileLoop = "false"

    ifFound = ""

    currentStructure = ""

    breakType = ""

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
                    stack.append(currentNode)
                    lastNode = "CommonNode"
                    currentStructure = ""
                    # if caller == "Student" and traversedNodes.count(currentNode) > 1:
                    #     studIfElseStepInfoDictList.append(stepDetailsDictionary.copy())
                    #     stepDetailsDictionary.clear()
                    if not (commonNodes or whileNodes or doWhileNodes):
                        nestedLevel = 0
                        breakType = "Condition"
                        return lastNode, previousNode, ifNodes, ifDictionary, nestedLevel, breakType
                    else:
                        continueWithFlow = 'true'
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
            currentNodeInfo = graph.data("MATCH (node:" + caller + ") WHERE node.key= {key} RETURN node",
                                            parameters={"key": currentNode})

            if not currentNodeInfo[0]['node']['symbol'] == "Start":
                currentNodeOtherParents = graph.data("MATCH (parent:" + caller + ")-[:TO|YES|NO]->(child:" + caller + ") WHERE "
                                                        "child.key= {childKey} and parent.key <> {prevParentKey} RETURN parent",
                                                        parameters={"childKey": currentNode,
                                                                    "prevParentKey": previousNode})

                # CONSTRAINT: cannot put do while structures nested in other structures due to identification and traversal issues
                if not (whileNodes or doWhileNodes and commonNodes) and isDoWhileLoop == "false":
                    loopcount = 0
                    while loopcount < len(currentNodeOtherParents):
                        if not currentNodeOtherParents[loopcount]['parent']['key'] in traversedNodes and \
                                currentNodeOtherParents[loopcount]['parent']['symbol'] == "Decision":
                            isDoWhileLoop = "true"
                        loopcount = loopcount + 1

                # this check is for do while, as symbols inside loop must not be added to dictionary until the loop decision is reached
                if not isDoWhileLoop == "true":
                    if currentNodeInfo[0]['node']['symbol'] == "End":
                        breakType = "End"
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
                    breakType = "End"
                    break

                if currentNodeInfo[0]['node']['symbol'] == "Decision":
                    if traversedNodes.count(currentNode) == 1:
                        if caller == "Teacher" and currentNodeInfo[0]['node']['numberExpected'] and currentNodeInfo[0]['node']['stepMark']:
                            addStepMarkDetailsToDictionary('noOfDecisions', 'totDecisionMarks', stepDetailsDictionary,
                                                           currentNodeInfo, 0)
                        elif caller == "Student":
                            addStepMarkDetailsToDictionary('noOfDecisions', 'Student', stepDetailsDictionary,
                                                           currentNodeInfo, 1)
                        nestedLevel = nestedLevel + 1

                    # if caller == "Student" and traversedNodes.count(currentNode) == 1 and studIfElseStepInfoDictList \
                    #         and currentStructure == "IfElseIf":
                    #     studIfElseStepInfoDictList.append(stepDetailsDictionary.copy())
                    #     stepDetailsDictionary.clear()
                    # elif caller == "Teacher" and traversedNodes.count(currentNode) == 1 and currentStructure == "IfElseIf":
                    #     lastNode = "Decision"
                    #     previousNode = currentNode
                    #     return lastNode, previousNode, ifNodes, ifDictionary

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

                    if ((yesCurrentChildNode[0]['child']['key'] in traversedNodes or
                            noCurrentChildNode[0]['child']['key'] in traversedNodes) and
                            traversedNodes.count(currentNode) == 1 and not (whileNodes or doWhileNodes or commonNodes)):

                        doWhileFound = "true"
                        breakType = "Loop"

                        if not currentStructure:
                            currentStructure = "DoWhile"

                        if yesCurrentChildNode[0]['child']['key'] in traversedNodes:
                            if traversedNodes.count(currentNode) == 1:
                                stack.append(yesCurrentChildNode[0]['child']['key'])
                                doWhileNodes.append(currentNode)
                            elif traversedNodes.count(currentNode) > 1:
                                stack.append(noCurrentChildNode[0]['child']['key'])
                                isDoWhileLoop = "false"
                                currentStructure = ""
                        elif noCurrentChildNode[0]['child']['key'] in traversedNodes:
                            if traversedNodes.count(currentNode) == 1:
                                stack.append(noCurrentChildNode[0]['child']['key'])
                                doWhileNodes.append(currentNode)
                            elif traversedNodes.count(currentNode) > 1:
                                stack.append(yesCurrentChildNode[0]['child']['key'])
                                isDoWhileLoop = "false"
                                currentStructure = ""

                        if traversedNodes.count(currentNode) > 1:
                            visitedNodes.append(currentNode)
                            if doWhileNodes[0] == currentNode:
                                lastNode = "Decision"
                                previousNode = currentNode
                                nestedLevel = 0
                                return lastNode, previousNode, ifNodes, ifDictionary, nestedLevel, breakType
                            doWhileNodes.pop()
                    else:
                        if (len(whileNodes) == 0 and traversedNodes.count(currentNode) == 1) or \
                                (len(whileNodes) == 1 and traversedNodes.count(currentNode) == 2) or \
                                (len(whileNodes) == 0 and traversedNodes.count(currentNode) == 2):
                        # if traversedNodes.count(currentNode) == 1 or traversedNodes.count(currentNode) == 2:
                            loopPath = graph.data("MATCH (currentNode:" + caller + ")-[r:YES|NO]->(nextNode:" + caller +
                                                  ")-[*]->(currentNode:" + caller + ") WHERE currentNode.key = "
                                                  "{currentNodeKey} RETURN DISTINCT TYPE(r)",
                                                  parameters={"currentNodeKey": currentNode})
                        elif (len(whileNodes) == 1 and traversedNodes.count(currentNode) == 1) or \
                                (len(whileNodes) == 2 and traversedNodes.count(currentNode) == 2):
                            loopPath = graph.data(
                                "MATCH path = (currentNode:" + caller + ")-[r:YES|NO]->(nextNode:" + caller + ")-[*]->"
                                "(currentNode:" + caller + ") WHERE currentNode.key = {currentNodeKey} "
                                "WITH path, r MATCH (previousIfNode: " + caller + ") WHERE previousIfNode.key = "
                                "{previousIfNodeKey} AND NOT previousIfNode IN NODES(path) RETURN TYPE(r)",
                                parameters={"currentNodeKey": currentNode, "previousIfNodeKey": whileNodes[0]})
                        elif (len(whileNodes) == 2 and traversedNodes.count(currentNode) == 1) or \
                                (len(whileNodes) == 3 and traversedNodes.count(currentNode) == 2):
                            loopPath = graph.data(
                                "MATCH path = (currentNode:" + caller + ")-[r:YES|NO]->(nextNode:" + caller + ")-[*]->"
                                "(currentNode:" + caller + ") WHERE currentNode.key = {currentNodeKey} "
                                "WITH path, r MATCH (previousIfNodeOne: " + caller + "), "
                                "(previousIfNodeTwo: " + caller + ") WHERE (previousIfNodeOne.key = "
                                "{previousIfNodeOneKey} AND NOT previousIfNodeOne IN NODES(path)) AND "
                                "(previousIfNodeTwo.key = {previousIfNodeTwoKey} AND NOT previousIfNodeTwo "
                                "IN NODES(path)) RETURN TYPE(r)",
                                parameters={"currentNodeKey": currentNode,
                                            "previousIfNodeOneKey": whileNodes[0],
                                            "previousIfNodeTwoKey": whileNodes[1]})

                        if not loopPath:
                            if doWhileFound == "false":
                                ifFound = "false"
                                breakType = "Condition"
                                currentStructure, ifFound = handleIfStructureTraversal(caller, graph, stack, currentNode,
                                                                                       noChildParents, yesChildParents,
                                                                                       traversedNodes, noCurrentChildNode,
                                                                                       yesCurrentChildNode, currentStructure,
                                                                                       commonNodes, ifNodes, ifDictionary,
                                                                                       visitedNodes, ifFound)
                        else:
                            if commonNodes or whileNodes or doWhileNodes:
                                if (len(whileNodes) == 0 and traversedNodes.count(currentNode) == 1) or \
                                        (len(whileNodes) == 1 and traversedNodes.count(currentNode) == 2) or \
                                        (len(whileNodes) == 0 and traversedNodes.count(currentNode) == 2):
                                # if traversedNodes.count(currentNode) == 1 or traversedNodes.count(currentNode) == 2:
                                    loopPathLength = graph.data(
                                        "MATCH path = (currentNode:" + caller + ")-[r:YES|NO]->(nextNode:" + caller +
                                        ")-[*]->(currentNode:" + caller + ") WHERE currentNode.key = " +
                                        "{currentNodeKey} RETURN length(path)", parameters={"currentNodeKey": currentNode})
                                elif (len(whileNodes) == 1 and traversedNodes.count(currentNode) == 1) or \
                                        (len(whileNodes) == 2 and traversedNodes.count(currentNode) == 2):
                                    loopPathLength = graph.data(
                                        "MATCH path = (currentNode:" + caller + ")-[r:YES|NO]->(nextNode:" + caller + ")-[*]->"
                                        "(currentNode:" + caller + ") WHERE currentNode.key = {currentNodeKey} "
                                        "WITH path, r MATCH (previousIfNode: " + caller + ") WHERE previousIfNode.key = "
                                        "{previousIfNodeKey} AND NOT previousIfNode IN NODES(path) RETURN length(path)",
                                        parameters={"currentNodeKey": currentNode, "previousIfNodeKey": whileNodes[0]})
                                elif (len(whileNodes) == 2 and traversedNodes.count(currentNode) == 1) or \
                                        (len(whileNodes) == 3 and traversedNodes.count(currentNode) == 2):
                                    loopPathLength = graph.data(
                                        "MATCH path = (currentNode:" + caller + ")-[r:YES|NO]->(nextNode:" + caller + ")-[*]->"
                                        "(currentNode:" + caller + ") WHERE currentNode.key = {currentNodeKey} "
                                        "WITH path, r MATCH (previousIfNodeOne: " + caller + "), "
                                        "(previousIfNodeTwo: " + caller + ") WHERE (previousIfNodeOne.key = "
                                        "{previousIfNodeOneKey} AND NOT previousIfNodeOne IN NODES(path)) AND "
                                        "(previousIfNodeTwo.key = {previousIfNodeTwoKey} AND NOT previousIfNodeTwo "
                                        "IN NODES(path)) RETURN length(path)",
                                        parameters={"currentNodeKey": currentNode,
                                                    "previousIfNodeOneKey": whileNodes[0],
                                                    "previousIfNodeTwoKey": whileNodes[1]})

                                curCommonNodePathLength = graph.data(
                                    "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(a:" + caller + ")-[*]->(commonNode:" +
                                    caller + "), path2 = (currentDecision:" + caller + ")-[:NO]->(b:" + caller + ")-[*]->" +
                                    "(commonNode:" + caller + ") WHERE currentDecision.key={currentNodeKey} and path1 <> path2 " +
                                    "RETURN length(path2)",
                                    parameters={"currentNodeKey": currentNode})

                                if not curCommonNodePathLength:
                                    curCommonNodePathLength = graph.data(
                                        "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(a:" + caller + ")-[*]->" +
                                        "(commonNode:" + caller + "), path2 = (currentDecision:" + caller + ")-[:NO]->" +
                                        "(commonNode:" + caller + ") WHERE currentDecision.key={currentNodeKey} and " +
                                        "path1 <> path2 RETURN length(path2)",
                                        parameters={"currentNodeKey": currentNode})

                                if not curCommonNodePathLength:
                                    curCommonNodePathLength = graph.data(
                                        "MATCH path1 = (currentDecision:" + caller + ")-[:YES]->(commonNode:" + caller + "), " +
                                        "path2 = (currentDecision:" + caller + ")-[:NO]->(b:" + caller + ")-[*]->(commonNode:" +
                                        caller + ") WHERE currentDecision.key={currentNodeKey} and path1 <> path2 RETURN " +
                                        "length(path1)", parameters={"currentNodeKey": currentNode})

                                if not curCommonNodePathLength:
                                    breakType = "Loop"
                                    lastNode, previousNode, ifNodes, ifDictionary, currentStructure = \
                                        handleWhileStructureTraversal(stack, loopPath, currentStructure, traversedNodes,
                                                                      currentNode, yesCurrentChildNode,
                                                                      noCurrentChildNode, whileNodes, ifNodes,
                                                                      ifDictionary, lastNode, previousNode)

                                    if traversedNodes.count(currentNode) > 1:
                                        visitedNodes.append(currentNode)
                                        if whileNodes[0] == currentNode and not (commonNodes or doWhileNodes):
                                            lastNode = "Decision"
                                            previousNode = currentNode
                                            nestedLevel = 0
                                            return lastNode, previousNode, ifNodes, ifDictionary, nestedLevel, breakType
                                        whileNodes.pop()
                                else:
                                    if loopPathLength[0]['length(path)'] > curCommonNodePathLength[0]['length(path2)']:
                                        ifFound = "false"
                                        breakType = "Condition"
                                        currentStructure, ifFound = handleIfStructureTraversal(caller, graph, stack,
                                                                                               currentNode, noChildParents,
                                                                                               yesChildParents,
                                                                                               traversedNodes,
                                                                                               noCurrentChildNode,
                                                                                               yesCurrentChildNode,
                                                                                               currentStructure, commonNodes,
                                                                                               ifNodes, ifDictionary,
                                                                                               visitedNodes, ifFound)
                                    else:
                                        breakType = "Loop"
                                        lastNode, previousNode, ifNodes, ifDictionary, currentStructure = \
                                            handleWhileStructureTraversal(stack, loopPath, currentStructure, traversedNodes,
                                                                          currentNode, yesCurrentChildNode,
                                                                          noCurrentChildNode, whileNodes, ifNodes,
                                                                          ifDictionary, lastNode, previousNode)

                                        if traversedNodes.count(currentNode) > 1:
                                            visitedNodes.append(currentNode)
                                            if whileNodes[0] == currentNode and not (commonNodes or doWhileNodes):
                                                lastNode = "Decision"
                                                previousNode = currentNode
                                                nestedLevel = 0
                                                return lastNode, previousNode, ifNodes, ifDictionary, nestedLevel, breakType
                                            whileNodes.pop()
                            else:
                                breakType = "Loop"
                                lastNode, previousNode, ifNodes, ifDictionary, currentStructure = \
                                    handleWhileStructureTraversal(stack, loopPath, currentStructure, traversedNodes,
                                                              currentNode, yesCurrentChildNode, noCurrentChildNode,
                                                              whileNodes, ifNodes, ifDictionary, lastNode, previousNode)

                                if traversedNodes.count(currentNode) > 1:
                                    visitedNodes.append(currentNode)
                                    if whileNodes[0] == currentNode and not (commonNodes or doWhileNodes):
                                        lastNode = "Decision"
                                        previousNode = currentNode
                                        nestedLevel = 0
                                        return lastNode, previousNode, ifNodes, ifDictionary, nestedLevel, breakType
                                    whileNodes.pop()

                    # if caller == "Student" and traversedNodes.count(currentNode) > 1 and currentStructure == "IfElse":
                    #     studIfElseStepInfoDictList.append(stepDetailsDictionary.copy())
                    #     stepDetailsDictionary.clear()
                    # elif caller == "Student" and currentStructure == "IfElseIf":
                    #     if traversedNodes.count(currentNode) == 1 and not studIfElseStepInfoDictList:
                    #         lastNode = "Decision"
                    #         previousNode = currentNode
                    #         return lastNode, previousNode, ifNodes, ifDictionary
                    #     elif traversedNodes.count(currentNode) > 1:
                    #         studIfElseStepInfoDictList.append(stepDetailsDictionary.copy())
                    #         stepDetailsDictionary.clear()
                    # else:
                    if not ((traversedNodes.count(currentNode) > 1 and ifFound == "true") or nestedLevel > 1):
                            # (len(commonNodes) >= 1 or len(whileNodes) >= 1 or len(doWhileNodes) >= 1)):
                        lastNode = "Decision"
                        # lastNode = currentStructure
                        previousNode = currentNode
                        # break
                        return lastNode, previousNode, ifNodes, ifDictionary, nestedLevel, breakType

            if not currentNodeInfo[0]['node']['symbol'] == "Decision":
                curChildNode = graph.data(
                    "MATCH (parent:" + caller + ")-[:TO]->(child:" + caller + ") WHERE parent.key= {key} RETURN child",
                    parameters={"key": currentNode})

                stack.append(curChildNode[0]['child']['key'])

            previousNode = currentNode

    return lastNode, previousNode, ifNodes, ifDictionary, nestedLevel, breakType


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

    teachDoWhileNodes = []
    teachWhileNodes = []

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

    studDoWhileNodes = []
    studWhileNodes = []

    teachPrevNode = -99
    studPrevNode = -99

    teachNestedLevel = 0
    studNestedLevel = 0

    teachBreakType = ""
    studBreakType = ""

    scoredStepMark = 0
    totNoOfAdditionalSteps = 0
    totNoOfDeletedSteps = 0

    feedback = ""

    markingFinished = "false"

    while markingFinished == "false":
        # endOrDecisionFound = "false"

        teacherLastNode = "End"
        studentLastNode = "End"

        teacherLastNode, teachPrevNode, teachIfNodes, teachIfDictionary, teachNestedLevel, teachBreakType = \
            traverseStepsAndHandleDetails('Teacher', graph,
                                                        teacherStack, teacherTraversedNodes,
                                                        teacherStepAndMarkInfo, teachVisitedNodes, teacherLastNode,
                                                        teachPrevNode, teachCommonNodes, teachIfNodes, teachIfDictionary,
                                                        teachMainIfCompletedNoOfPaths, teachDoWhileNodes, teachWhileNodes,
                                                        teachNestedLevel)

        studentLastNode, studPrevNode, studIfNodes, studIfDictionary, studNestedLevel, studBreakType = \
            traverseStepsAndHandleDetails('Student', graph,
                                                        studentStack, studentTraversedNodes,
                                                        studentStepInfo, studVisitedNodes, studentLastNode, studPrevNode,
                                                        studCommonNodes, studIfNodes, studIfDictionary,
                                                        studMainIfCompletedNoOfPaths, studDoWhileNodes, studWhileNodes,
                                                        studNestedLevel)

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

        elif (teacherLastNode == "Decision" and studentLastNode == "Decision") or (teacherLastNode == "CommonNode" and studentLastNode == "CommonNode"):
        # elif ((teacherLastNode == "If" or teacherLastNode == "IfNot") and (studentLastNode == "If" or
        #         studentLastNode == "IfNot")) or ((teacherLastNode == "While" or teacherLastNode == "DoWhile") and
        #         (studentLastNode == "While" or studentLastNode == "DoWhile")):
            scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = \
                callStepCountingForAllSymbols(teacherStepAndMarkInfo, studentStepInfo, scoredStepMark,
                                              totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback)

            teacherStepAndMarkInfo.clear()
            studentStepInfo.clear()

            if teacherLastNode == "Decision" and studentLastNode == "Decision":
                if (teachBreakType == "Condition" and studBreakType == "Loop") or \
                        (teachBreakType == "Loop" and studBreakType == "Condition"):

                    # one mark is deducted for the incorrect decision node type which will be identified as correct
                    # above based on the Decision node count
                    scoredStepMark = scoredStepMark - 1

                    if teachBreakType == "Condition" and studBreakType == "Loop":
                        caller = "TConditionSLoop"
                    elif teachBreakType == "Loop" and studBreakType == "Condition":
                        caller = "TLoopSCondition"

                    totNoOfDeletedSteps, feedback = getAllIncorrectNodes(caller, graph, teacherStack,
                                                                         totNoOfDeletedSteps,
                                                                         feedback, teacherTraversedNodes,
                                                                         teachVisitedNodes)

                    allocateMarksAndSaveToDatabase(scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps,
                                                   feedback,
                                                   #   flowchartQuestionId, studentAnswerId)
                                                   46, 135)

                    markingFinished = "true"
        elif teacherLastNode == "End" and studentLastNode == "Decision":
            scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = \
                callStepCountingForAllSymbols(teacherStepAndMarkInfo, studentStepInfo, scoredStepMark,
                                              totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback)

            totNoOfAdditionalSteps, feedback = getAllIncorrectNodes('Student', graph, studentStack, totNoOfAdditionalSteps,
                                                                    feedback, studentTraversedNodes, studVisitedNodes)

            allocateMarksAndSaveToDatabase(scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback,
                                           #   flowchartQuestionId, studentAnswerId)
                                           46, 135)

            markingFinished = "true"
        elif teacherLastNode == "Decision" and studentLastNode == "End":
            scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = \
                callStepCountingForAllSymbols(teacherStepAndMarkInfo, studentStepInfo, scoredStepMark,
                                              totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback)

            totNoOfDeletedSteps, feedback = getAllIncorrectNodes('Teacher', graph, teacherStack, totNoOfDeletedSteps,
                                                                 feedback, teacherTraversedNodes, teachVisitedNodes)

            allocateMarksAndSaveToDatabase(scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback,
                                           #   flowchartQuestionId, studentAnswerId)
                                           46, 135)

            markingFinished = "true"

        # elif teacherLastNode == "Decision" and studentLastNode == "CommonNode":
        #     while not teacherLastNode == "CommonNode":
        #         scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = \
        #             callStepCountForAllPossibilities(teacherStepAndMarkInfo, studIfElseStepInfoDictList, scoredStepMark,
        #                                          totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback)
        #
        #         teacherStepAndMarkInfo.clear()
        #
        #         teacherLastNode, teachPrevNode, teachIfNodes, teachIfDictionary = traverseStepsAndHandleDetails('Teacher',
        #                                                                                                         graph,
        #                                                                                                         teacherStack,
        #                                                                                                         teacherTraversedNodes,
        #                                                                                                         teacherStepAndMarkInfo,
        #                                                                                                         teachVisitedNodes,
        #                                                                                                         teacherLastNode,
        #                                                                                                         teachPrevNode,
        #                                                                                                         teachCommonNodes,
        #                                                                                                         teachIfNodes,
        #                                                                                                         teachIfDictionary,
        #                                                                                                         teachMainIfCompletedNoOfPaths,
        #                                                                                                         teachIfElseStepInfoDictList)
        #
        #     if teacherLastNode == "CommonNode" and studentLastNode == "CommonNode":
        #         scoredStepMark, totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback = \
        #             callStepCountForAllPossibilities(teacherStepAndMarkInfo, studIfElseStepInfoDictList, scoredStepMark,
        #                                              totNoOfAdditionalSteps, totNoOfDeletedSteps, feedback)
        #
        #         teacherStepAndMarkInfo.clear()
        #         studentStepInfo.clear()
        #         studIfElseStepInfoDictList.clear()

markStudDFSFlowchartAnswer()
