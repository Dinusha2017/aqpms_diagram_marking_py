import py2neo
import pymysql

import py_stringmatching
from difflib import SequenceMatcher
from TextMatch import getPhraseSimilarity

import re

from CreateGraph import connectToGraph

from py2neo import Graph

import json

mySQLhostname = '178.128.158.92'
mySQLusername = 'aqpmsuser'
mySQLpassword = 'aqpms'
mySQLdatabase = 'question_marking_system'

def addTheOnlyUnmatchedNode(caller, graph,
                            notMatchedParentTeacherNodes,
                            teachStack,
                            studChildNodesList,
                            matchedLevelStudentNodes,
                            studStack,
                            totNoOfSubstitutedNodes,
                            feedback,
                            studentVisitedNodes,
                            teacherCurrentNode,
                            currentStudText,
                            totNoOfOtherIncorrectNodes):

    teacherNode = notMatchedParentTeacherNodes.pop()

    teacherNodeText = graph.data(
        "MATCH (node:Teacher) WHERE node.key= {key} RETURN node.text",
        parameters={"key": teacherNode})

    teacherCurrentText = graph.data(
        "MATCH (node:Teacher) WHERE node.key= {key} RETURN node.text",
        parameters={"key": teacherCurrentNode})

    # print(teacherNodeText[0]['node.text'])
    print(teacherCurrentNode)
    print(teacherCurrentText)

    print('^^^^^^^^^^^ BEFORE one substituted function FOR LOOP')

    for studentChild in studChildNodesList:
        print('^^^^^^^^^^^ INSIDE one substituted function FOR LOOP')

        if not studentChild['child']['key'] in matchedLevelStudentNodes and not studentChild['child']['key'] in studentVisitedNodes:
            print('^^^^^^^^^^^ INSIDE if and after visited node check')
            # print('not matched student node: ' + str(studentChild))

            teachStack.append(teacherNode)

            studStack.append(studentChild['child']['key'])
            totNoOfSubstitutedNodes = totNoOfSubstitutedNodes + 1
            feedback = feedback + 'The block:' + studentChild['child']['text'] + ' connected to block:' + currentStudText +\
                       ' is substituted and should be: ' + teacherNodeText[0]['node.text'] + '. '

        elif not studentChild['child']['key'] in matchedLevelStudentNodes and studentChild['child']['key'] in studentVisitedNodes:
            totNoOfSubstitutedNodes = totNoOfSubstitutedNodes + 1
            feedback = feedback + 'The block connection is substituted and should be from:' + teacherCurrentText[0]['node.text'] + \
                       ' to: ' + teacherNodeText[0]['node.text'] + '. '
            totNoOfOtherIncorrectNodes = totNoOfOtherIncorrectNodes + 1


    if caller == 'NotMatchedNode':
        return totNoOfSubstitutedNodes, totNoOfOtherIncorrectNodes, feedback
    elif caller == 'NotMatchedChildrenNode':
        return totNoOfOtherIncorrectNodes, feedback


def checkForCurrentNodeChildMatch(caller, graph,
                                  matchedStudentNodes,
                                  notMatchedParentTeacherNodes,
                                  studChildNodesList,
                                  studVisitedNodes,
                                  studStack,
                                  teachStack,
                                  feedback,
                                  currentStudText):

    # print('^^^^^INSIDE checkForCurrentNodeChildMatch')
    # print(notMatchedParentTeacherNodes)

    handledStudentNodeList = matchedStudentNodes

    againNotMatchedTeacherNodes = []

    for notMatchedTeacherNode in notMatchedParentTeacherNodes:

        # print('INSIDE TEACHER FOR LOOOOOOP')

        teacherNodeText = graph.data(
            "MATCH (node:Teacher) WHERE node.key= {key} RETURN node.text",
            parameters={"key": notMatchedTeacherNode})

        notMatchedTeacherChildNodes = graph.data(
            "MATCH (parent:Teacher)-[:TO]->(child:Teacher) WHERE parent.key= {key} RETURN child",
            parameters={"key": notMatchedTeacherNode})

        # Check only one child node from teacher to student's each unmatched nodes' child nodes
        teacherChildText = notMatchedTeacherChildNodes[0]['child']['text']

        matchingStudentNodeFound = 'false'

        for studentChild in studChildNodesList:

            # print('INSIDE STUDENT FOR LOOOOOOP')

            if matchingStudentNodeFound == 'true':
                break

            if not studentChild['child']['key'] in handledStudentNodeList and not studentChild['child'][
                                                                                      'key'] in studVisitedNodes:
                notMatchedStudentChildNodes = graph.data(
                    "MATCH (parent:Student)-[:TO]->(child:Student) WHERE parent.key= {key} RETURN child",
                    parameters={"key": studentChild['child']['key']})

                for notMatchedStudentChild in notMatchedStudentChildNodes:
                    textSim = getPhraseSimilarity(teacherChildText, notMatchedStudentChild['child']['text'])

                    if re.match(teacherChildText, notMatchedStudentChild['child']['text'], re.IGNORECASE) or textSim >= 0.55:
                        print('the text')
                        print(teacherChildText)
                        print(notMatchedStudentChild['child']['text'])
                        print('threshold similarity added to Student stack in NOT MATCHED SIMILARITY GREATER ' + str(
                            textSim))

                        studStack.append(studentChild['child']['key'])
                        teachStack.append(notMatchedTeacherNode)

                        if caller == "substitutedCaller":
                            feedback = feedback + 'The block:' + studentChild['child']['text'] + ' connected to block:' +\
                                       currentStudText + ' is substituted and should be:' + teacherNodeText[0]['node.text'] + '. '
                        elif caller == "additionalSubstitutedCaller" or caller == "deletedSubstitutedCaller":
                            feedback = feedback + 'block: ' + studentChild['child']['text'] + ' connected to block:' +\
                                       currentStudText + ' is substituted and should be:' + \
                                       teacherNodeText[0]['node.text'] + ' and '

                        print('feedback: ' + feedback)

                        handledStudentNodeList.append(studentChild['child']['key'])

                        matchingStudentNodeFound = 'true'
                        break

        if matchingStudentNodeFound == 'false':
            againNotMatchedTeacherNodes.append(notMatchedTeacherNode)

    # print('^^^^^^^^^^^HANDLED STUDENT NODE LIST')
    # print(handledStudentNodeList)

    return againNotMatchedTeacherNodes, handledStudentNodeList, feedback


# detect rest of the additional/deleted/additional or substituted/deleted or substituted blocks
def detectUndetectedBlocks(caller,
                           graph,
                           nodeStack,
                           visitedNodeSet,
                           feedback,
                           totNoOfIncorrectNodes):

    while nodeStack:

        currentNode = nodeStack.pop()

        if caller == "additionalNodes" or caller == "addOrSubNodes" or caller == "substitutedNodes":
            currentNodeText = graph.data(
                "MATCH (node:Student) WHERE node.key= {key} RETURN node.text",
                parameters={"key": currentNode})

            currentNodeChildNodes = graph.data(
                "MATCH (parent:Student)-[:TO]->(child:Student) WHERE parent.key = {key} RETURN child",
                parameters={"key": currentNode})
        elif caller == "deletedNodes" or caller == "delOrSubNodes":
            currentNodeText = graph.data(
                "MATCH (node:Teacher) WHERE node.key= {key} RETURN node.text",
                parameters={"key": currentNode})

            currentNodeChildNodes = graph.data(
                "MATCH (parent:Teacher)-[:TO]->(child:Teacher) WHERE parent.key = {key} RETURN child",
                parameters={"key": currentNode})

        currentNodeChildNodesList = list(currentNodeChildNodes)

        for childNode in currentNodeChildNodesList:

            if not childNode['child']['text'] == 'end':
                if not childNode['child']['key'] in visitedNodeSet:
                    totNoOfIncorrectNodes = totNoOfIncorrectNodes + 1

                    if caller == "additionalNodes":
                        feedback = feedback + 'Additional Block:' + childNode['child']['text'] +\
                                   ' connected to block:' + currentNodeText[0]['node.text'] + '. '
                    elif caller == "deletedNodes":
                        feedback = feedback + 'Missing Block:' + childNode['child']['text'] +\
                                   ' connected to block:' + currentNodeText[0]['node.text'] + '. '
                    elif caller == "substitutedNodes":
                        feedback = feedback + 'Substituted Block:' + childNode['child']['text'] +\
                                   ' connected to block:' + currentNodeText[0]['node.text'] + '. '
                    elif caller == "addOrSubNodes":
                        feedback = feedback + 'Additional/Substituted Block:' + childNode['child']['text'] +\
                                   ' connected to block:' + currentNodeText[0]['node.text'] + '. '
                    elif caller == "delOrSubNodes":
                        feedback = feedback + 'Missing/Substituted Block:' + childNode['child']['text'] +\
                                   ' connected to block:' + currentNodeText[0]['node.text'] + '. '

                    nodeStack.append(childNode['child']['key'])
                elif childNode['child']['key'] in visitedNodeSet:
                    continue

    return feedback, totNoOfIncorrectNodes



def allocateMarksAndSaveToDatabase(noOfMatchedNodes,
                                   noOfAdditionalNodes,
                                   noOfDeletedNodes,
                                   noOfSubstitutedNodes,
                                   totNoOfOtherSubstitutedNodes,
                                   totNoOfOtherIncorrectNodes,
                                   feedback,
                                   processQuestionId,
                                   studentAnswerId):
    connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)
    cur = connection.cursor()
    cur.execute("SELECT textMark, sequenceMark FROM process_question WHERE processqId = %s", (processQuestionId))
    resultSet = cur.fetchone()
    print('starting mark allocation...')

    textMark = resultSet[0]
    sequenceMark = resultSet[1]

    sequenceMarkForAddDeleteDeductions = (70/100) * sequenceMark
    print('sequenceMarkForAddDeleteDeductions: ' + str(sequenceMarkForAddDeleteDeductions))

    totalAddDeleteDiff = noOfAdditionalNodes + noOfDeletedNodes + totNoOfOtherIncorrectNodes

    scoredTextMark = noOfMatchedNodes * textMark

    if noOfMatchedNodes == 0:
        scoredSequenceMark = 0
    else:
        # maximum number of errors for additions and deletions that are allowed is 5
        if totalAddDeleteDiff <= 5:
            scoredSequenceMark = sequenceMark - (totalAddDeleteDiff/5) * sequenceMarkForAddDeleteDeductions
        else:
            scoredSequenceMark = sequenceMark - sequenceMarkForAddDeleteDeductions

    scoredFullMark = scoredTextMark + scoredSequenceMark

    print(scoredTextMark)
    print(scoredSequenceMark)
    print(noOfAdditionalNodes)
    print(noOfDeletedNodes)
    print(totNoOfOtherIncorrectNodes)

    cur.execute("UPDATE process_stud_answer SET textMark = %s, sequenceMark = %s WHERE processStudAnsId = %s",
                (scoredTextMark, scoredSequenceMark, studentAnswerId))

    cur.execute("UPDATE student_answer SET scoredMark = %s, feedback = %s, markedStatus = %s WHERE studAnswerId = %s",
                (scoredFullMark, feedback, "true", studentAnswerId))
    cur.close()
    connection.close()


def markStudDFSBlockAnswer(processQuestionId, studentAnswerId):
    # Connect to Graph
    graph = connectToGraph()

    whiteSpaceTokenizer = py_stringmatching.WhitespaceTokenizer(return_set=True)
    jaccard = py_stringmatching.Jaccard()
    levenshtein = py_stringmatching.Levenshtein()

    teacherStartNodeKey = graph.data(
        "MATCH (node:Teacher) WHERE node.text='start' RETURN node.key")
    studentStartNodeKey = graph.data(
        "MATCH (node:Student) WHERE node.text='start' RETURN node.key")

    teachStack = [teacherStartNodeKey[0]['node.key']]
    studStack = [studentStartNodeKey[0]['node.key']]

    teachVisitedNodes = []
    studVisitedNodes = []

    # keeps track of the nodes matched in each level
    matchedTeacherNodes = []
    matchedStudentNodes = []

    notMatchedParentTeacherNodes = []

    # keeps track of all the nodes visited throughout graph traversal and a node is added to this each time it is visited
    allMatchedTeachNodes = []
    allMatchedStudNodes = []

    additionalNodes = []
    deletedNodes = []
    substitutedNodes = []
    addOrSubNodes = []
    delOrSubNodes = []

    totNoOfAdditionalNodes = 0
    totNoOfDeletedNodes = 0
    totNoOfSubstitutedNodes = 0
    totNoOfOtherIncorrectNodes = 0
    totNoOfOtherSubstitutedNodes = 0

    totNoOfMatchedNodes = 0

    feedback = ""

    while teachStack or studStack:

        if teachStack and studStack:

            teachCurrent = teachStack.pop()
            studCurrent = studStack.pop()

            teacherCurrentText = graph.data(
                "MATCH (node:Teacher) WHERE node.key= {key} RETURN node.text",
                parameters={"key": teachCurrent})

            studentCurrentText = graph.data(
                "MATCH (node:Student) WHERE node.key= {key} RETURN node.text",
                parameters={"key": studCurrent})

            print('teacher current........................')
            print(teacherCurrentText)
            print('student current........................')
            print(studentCurrentText)


            teacherChildNodes = graph.data(
                "MATCH (parent:Teacher)-[:TO]->(child:Teacher) WHERE parent.key= {key} RETURN child",
                    parameters={"key": teachCurrent})     #teacherStartNodeKey[0]['node.key']

            studentChildNodes = graph.data(
                "MATCH (parent:Student)-[:TO]->(child:Student) WHERE parent.key= {key} RETURN child",
                    parameters={"key": studCurrent})     #studentStartNodeKey[0]['node.key']


            teachChildNodesList = list(teacherChildNodes)

            studChildNodesList = list(studentChildNodes)

            for teacherChild in teachChildNodesList:

                    teachText = teacherChild['child']['text']
                    # teachTextTokens = whiteSpaceTokenizer.tokenize(teacherChild['child']['text'])

                    print(teachText)

                    matchFound = 'false'

                    for studentChild in studChildNodesList:
                        if not studentChild['child']['key'] in matchedStudentNodes:
                            print('current stud child')
                            print(studentChild['child']['text'])
                            childText = studentChild['child']['text']
                            # studTextTokens = whiteSpaceTokenizer.tokenize(studentChild['child']['text'])
                            #
                            # jaccard_score = jaccard.get_raw_score(teachTextTokens, studTextTokens)
                            # lev_score = levenshtein.get_sim_score(teachText, childText)
                            # similarity = SequenceMatcher(None, teachText, childText).ratio()

                            synsetSim_score = getPhraseSimilarity(teachText, childText)

                            print(teachText)
                            print(childText)
                            #
                            # print('lev: ' + str(lev_score))
                            # print('similarity: ' + str(similarity))
                            print('synset similarity: ' + str(synsetSim_score))

                            # if lev_score > 0.1:
                            # if similarity > 0.4:
                            if re.match(teachText, childText, re.IGNORECASE) or synsetSim_score >= 0.55:
                                print('threshold similarity added to Student stack')

                                feedback = feedback + 'The block:' + studentChild['child']['text'] + \
                                           ' connected to block:' + studentCurrentText[0]['node.text'] + ' is correct. '

                                matchFound = 'true'

                                if not teacherChild['child']['key'] in teachVisitedNodes:
                                    studStack.append(studentChild['child']['key'])

                                    teachStack.append(teacherChild['child']['key'])

                                    if not studentChild['child']['key'] in allMatchedStudNodes and not studentChild['child']['text'] == 'end':
                                        totNoOfMatchedNodes = totNoOfMatchedNodes + 1

                                    allMatchedTeachNodes.append(teacherChild['child']['key'])
                                    allMatchedStudNodes.append(studentChild['child']['key'])

                                if len(teachChildNodesList) > len(studChildNodesList):
                                    matchedTeacherNodes.append(teacherChild['child']['key'])

                                    # add to student matched node set too to check while looping through the current level children (above)
                                    matchedStudentNodes.append(studentChild['child']['key'])
                                elif len(teachChildNodesList) < len(studChildNodesList):
                                    matchedStudentNodes.append(studentChild['child']['key'])
                                else:
                                    matchedStudentNodes.append(studentChild['child']['key'])

                                break

                    if matchFound == 'false' and not teacherChild['child']['key'] in teachVisitedNodes:     # len(teachChildNodesList) == len(studChildNodesList) and
                        notMatchedParentTeacherNodes.append(teacherChild['child']['key'])
                    elif matchFound == 'false' and teacherChild['child']['key'] in teachVisitedNodes:
                        feedback = feedback + 'The block:' + teacherChild['child']['text'] + \
                                   ' should be connected to block:' + teacherCurrentText[0]['node.text'] + '. '
                        totNoOfOtherIncorrectNodes = totNoOfOtherIncorrectNodes + 1



            print('matched teacher nodes: ')
            print(allMatchedTeachNodes)
            print('matched student nodes: ')
            print(allMatchedStudNodes)



            if len(teachChildNodesList) == len(studChildNodesList)and len(notMatchedParentTeacherNodes) == 1:

                print('^^^ONE SUBSTITUTED NODE')

                totNoOfSubstitutedNodes, totNoOfOtherIncorrectNodes, feedback = \
                    addTheOnlyUnmatchedNode('NotMatchedNode', graph, notMatchedParentTeacherNodes,
                                        teachStack, studChildNodesList, matchedStudentNodes,
                                        studStack, totNoOfSubstitutedNodes, feedback, studVisitedNodes,
                                        teachCurrent, studentCurrentText[0]['node.text'], totNoOfOtherIncorrectNodes)


            elif len(teachChildNodesList) == len(studChildNodesList) and len(notMatchedParentTeacherNodes) > 1:

                totNoOfSubstitutedNodes = totNoOfSubstitutedNodes + len(notMatchedParentTeacherNodes)

                againNotMatchedTeacherNodes, handledStudentNodeList, feedback = checkForCurrentNodeChildMatch(
                                              'substitutedCaller', graph, matchedStudentNodes,
                                              notMatchedParentTeacherNodes, studChildNodesList,
                                              studVisitedNodes, studStack, teachStack, feedback, studentCurrentText[0]['node.text'])

                if len(againNotMatchedTeacherNodes) == 1:
                    print('^^^^^^^^^^^^^^AGAIN NOT MATCHED ONLY 1')
                    totNoOfOtherIncorrectNodes, feedback = addTheOnlyUnmatchedNode('NotMatchedChildrenNode', graph, againNotMatchedTeacherNodes,
                                                        teachStack, studChildNodesList,
                                                        handledStudentNodeList,
                                                        studStack, totNoOfSubstitutedNodes,
                                                        feedback, studVisitedNodes, teachCurrent,
                                                        studentCurrentText[0]['node.text'], totNoOfOtherIncorrectNodes)

                elif len(againNotMatchedTeacherNodes) > 1:
                    print('^^^^^^^^^^^^^^AGAIN NOT MATCHED MANYYYY')
                    for studentChild in studChildNodesList:
                        if not studentChild['child']['key'] in handledStudentNodeList and not studentChild['child']['key'] in studVisitedNodes:
                            feedback = feedback + 'The block:' + studentChild['child']['text'] + \
                                               ' connected to block:' + studentCurrentText[0]['node.text'] + ' is substituted, and it '

                            for againNotTeacherNode in againNotMatchedTeacherNodes:
                                teacherNodeText = graph.data(
                                    "MATCH (node:Teacher) WHERE node.key= {key} RETURN node.text",
                                    parameters={"key": againNotTeacherNode})

                                feedback = feedback + ' should be:' + teacherNodeText[0]['node.text'] + ' or'

                            feedback = feedback + ' one of the mentioned blocks. The immediate blocks that follow ' +\
                                       'this block:' + studentChild['child']['text'] + ' are also wrong. Please check them. '

                            substitutedNodes.append(studentChild['child']['key'])



            # print('^^^^^^^^^^^BEFORE IF')
            # print(notMatchedParentTeacherNodes)

            # handles scenario where student graph has deleted child nodes for the current node under consideration
            if len(teachChildNodesList) > len(studChildNodesList):
                totNoOfDeletedNodes = totNoOfDeletedNodes + (len(teachChildNodesList) - len(studChildNodesList))

                if len(matchedStudentNodes) == len(studChildNodesList):
                    for child in teachChildNodesList:
                        if not child['child']['key'] in matchedTeacherNodes and not child['child']['key'] in teachVisitedNodes:
                            feedback = feedback + 'Missing Block:' + child['child']['text'] + \
                                               ' should be connected to block:' + studentCurrentText[0]['node.text'] + '. '
                            deletedNodes.append(child['child']['key'])
                elif len(matchedStudentNodes) < len(studChildNodesList):
                    feedback = feedback + 'There is/are ' + str(len(teachChildNodesList) - len(studChildNodesList)) + \
                               ' missing block(s) that should be connected to block:' + studentCurrentText[0]['node.text'] + \
                               ' and ' + str(len(studChildNodesList) - len(matchedStudentNodes)) + \
                               ' block(s) connected to block:' + studentCurrentText[0]['node.text'] + \
                               ' is/are substituted - The incorrect blocks are '

                    againNotMatchedTeacherNodes, handledStudentNodeList, feedback = checkForCurrentNodeChildMatch(
                                'deletedSubstitutedCaller', graph, matchedStudentNodes,
                                notMatchedParentTeacherNodes, studChildNodesList,
                                studVisitedNodes, studStack, teachStack, feedback, studentCurrentText[0]['node.text'])

                    # print('^^^^^^^^^^^^^^^^^^DELETED SCENARIO')
                    # print(againNotMatchedTeacherNodes)

                    if len(handledStudentNodeList) == len(studChildNodesList):
                        for child in teachChildNodesList:
                            if child['child']['key'] in againNotMatchedTeacherNodes and not child['child'][
                                                                                            'key'] in teachVisitedNodes:
                                feedback = feedback + 'block:' + child['child']['text'] + \
                                           ' that should be connected to block:' + studentCurrentText[0]['node.text'] +\
                                           ' is missing and '
                                deletedNodes.append(child['child']['key'])

                    elif len(handledStudentNodeList) < len(studChildNodesList):
                        for child in teachChildNodesList:
                            if child['child']['key'] in againNotMatchedTeacherNodes and not child['child'][
                                                                                            'key'] in teachVisitedNodes:
                                feedback = feedback + ' block:' + child['child']['text'] + \
                                           ' that should be/is connected to block:' + studentCurrentText[0]['node.text'] + \
                                           ' is deleted/substituted and the immediate child blocks of this block are also wrong, please check them, and '

                                delOrSubNodes.append(child['child']['key'])

                    feedback = feedback + 'please check all these incorrect blocks. '



            # handles scenario where student graph has additional child nodes for the current node under consideration
            elif len(teachChildNodesList) < len(studChildNodesList):
                totNoOfAdditionalNodes = totNoOfAdditionalNodes + (len(studChildNodesList) - len(teachChildNodesList))

                # handles scenario where all teacher nodes are matched and there are additional nodes
                if len(matchedStudentNodes) == len(teachChildNodesList):
                    for child in studChildNodesList:
                        if not child['child']['key'] in matchedStudentNodes and not child['child']['key'] in studVisitedNodes:
                            feedback = feedback + 'Additional Block:' + child['child']['text'] +\
                                       ' is connected to block:' + studentCurrentText[0]['node.text'] + '. '
                            additionalNodes.append(child['child']['key'])
                        elif not child['child']['key'] in matchedStudentNodes and child['child']['key'] in studVisitedNodes:
                            feedback = feedback + 'Additional connection from block:' + studentCurrentText[0]['node.text'] +\
                                       ' to block:' + child['child']['text'] + '. '
                elif len(matchedStudentNodes) < len(teachChildNodesList):
                    # print('^^^^^^^^^^^^^^^^INSIDE ADDITIONAL')
                    # print(len(teachChildNodesList))
                    # print(len(matchedStudentNodes))

                    feedback = feedback + 'There is/are ' + str(len(studChildNodesList) - len(teachChildNodesList)) + \
                               ' additional block(s) connected to block:' + studentCurrentText[0]['node.text'] + ' and ' +\
                               str(len(teachChildNodesList) - len(matchedStudentNodes)) +\
                               ' block(s) connected to block:' + studentCurrentText[0]['node.text'] + ' is/are substituted - The incorrect blocks are '

                    againNotMatchedTeacherNodes, handledStudentNodeList, feedback = checkForCurrentNodeChildMatch(
                                        'additionalSubstitutedCaller', graph, matchedStudentNodes,
                                        notMatchedParentTeacherNodes, studChildNodesList,
                                        studVisitedNodes, studStack, teachStack, feedback, studentCurrentText[0]['node.text'])


                    if len(handledStudentNodeList) == len(teachChildNodesList):  # len(againNotMatchedTeacherNodes) == (len(studChildNodesList)-len(teachChildNodesList))

                        print('INSIDE DETECTED ADDITIONAL nodes')

                        for child in studChildNodesList:
                            if not child['child']['key'] in handledStudentNodeList and not child['child'][
                                                                                            'key'] in studVisitedNodes:
                                feedback = feedback + 'block:' + child['child']['text'] + ' connected to block:' +\
                                           studentCurrentText[0]['node.text'] + ' is additional and '
                                additionalNodes.append(child['child']['key'])

                    elif len(handledStudentNodeList) < len(teachChildNodesList):  # len(againNotMatchedTeacherNodes) > (len(studChildNodesList)-len(teachChildNodesList))
                        for child in studChildNodesList:
                            if not child['child']['key'] in handledStudentNodeList and not child['child'][
                                                                                            'key'] in studVisitedNodes:
                                feedback = feedback + ' block: ' + child['child']['text'] + ' connected to block:' +\
                                           studentCurrentText[0]['node.text'] +\
                                ' is additional/substituted and the immediate child blocks of this block are also wrong, please check them, and '

                                addOrSubNodes.append(child['child']['key'])

                    feedback = feedback + 'please check all these incorrect blocks. '


            matchedTeacherNodes = []
            matchedStudentNodes = []

            notMatchedParentTeacherNodes = []

            teachVisitedNodes.append(teachCurrent)
            studVisitedNodes.append(studCurrent)


            print('^^^^^^^^^no of substitutions: ' + str(totNoOfSubstitutedNodes))
            # print('feedback: ' + feedback)

        elif studStack and not teachStack:
            print('^^^^^^^^^^^^^^^STUDENT stack has moreeee.....')
            break


    # handles additional nodes down an additional node starting path
    if additionalNodes:
        feedback, totNoOfAdditionalNodes = detectUndetectedBlocks("additionalNodes", graph, additionalNodes,
                                                                  studVisitedNodes, feedback, totNoOfAdditionalNodes)

    # handles deleted nodes down a deleted node starting path
    if deletedNodes:
        feedback, totNoOfDeletedNodes = detectUndetectedBlocks("deletedNodes", graph, deletedNodes, teachVisitedNodes,
                                                               feedback, totNoOfDeletedNodes)

    # handles substituted nodes down a substituted node starting path
    if substitutedNodes:
        feedback, totNoOfOtherSubstitutedNodes = detectUndetectedBlocks("substitutedNodes", graph, substitutedNodes,
                                                                        studVisitedNodes, feedback,
                                                                        totNoOfOtherSubstitutedNodes)

    # handles additional/substituted nodes down a additional/substituted node starting path
    if addOrSubNodes:
        feedback, totNoOfOtherIncorrectNodes = detectUndetectedBlocks("addOrSubNodes", graph, addOrSubNodes,
                                                                      studVisitedNodes, feedback,
                                                                      totNoOfOtherIncorrectNodes)

    # handles deleted/substituted nodes down a deleted/substituted node starting path
    if delOrSubNodes:
        feedback, totNoOfOtherIncorrectNodes = detectUndetectedBlocks("delOrSubNodes", graph, delOrSubNodes,
                                                                      teachVisitedNodes, feedback,
                                                                      totNoOfOtherIncorrectNodes)




    if totNoOfAdditionalNodes == 0 and totNoOfDeletedNodes == 0 and totNoOfSubstitutedNodes == 0 and \
            totNoOfOtherSubstitutedNodes == 0 and totNoOfOtherIncorrectNodes == 0:
        print(totNoOfMatchedNodes)
        feedback = feedback + "Excellent Job! All the blocks and the flow are correct!" # Number of correct blocks: " + ". "
        print(feedback)
    else:
        feedback = feedback + "Number of correct blocks except start and end blocks: " + str(totNoOfMatchedNodes) + ". "
        print(feedback)

    allocateMarksAndSaveToDatabase(totNoOfMatchedNodes, totNoOfAdditionalNodes, totNoOfDeletedNodes,
                                   totNoOfSubstitutedNodes, totNoOfOtherSubstitutedNodes, totNoOfOtherIncorrectNodes,
                                   feedback, processQuestionId, studentAnswerId)


# markStudDFSBlockAnswer()
