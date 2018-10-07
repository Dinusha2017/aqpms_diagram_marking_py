import pymysql

import itertools

from py2neo import Node

from CreateGraph import connectToGraph
# from CreateGraph import createBDDNode, createBDDRelationship

mySQLhostname = '104.248.116.101'
mySQLusername = 'aqpmsuser'
mySQLpassword = 'aqpms'
mySQLdatabase = 'question_marking_system'

def handleGateInputsAndQueue(childNode,
                             childNodeDetails,
                             currentInput,
                             childParents,
                             queue):
    if not childNode['child']['inputs']:
        print('INSIDE adding first input')
        childNodeDetails['inputs'] = [currentInput]

        if len(childParents) == 1:
            queue.insert(0, childNode['child']['key'])
    else:
        print('INSIDE appending input')
        # print(len(childNode['child']['inputs']))
        # print(len(childNode['child']['inputs'] + [currentInput]))
        inputs = childNode['child']['inputs']
        childNodeDetails['inputs'] = inputs + [currentInput]

        if len(childNode['child']['inputs'] + [currentInput]) == len(childParents):
            queue.insert(0, childNode['child']['key'])


def getInputForAndOrNandNor(currentNodeInfo,
                            curInput,
                            expectedBinaryNum,
                            breakInput):
    inputs = currentNodeInfo[0]['node']['inputs']

    currentInput = curInput

    for binaryNum in inputs:
        if binaryNum == expectedBinaryNum:
            currentInput = breakInput
            break

    return currentInput


def getInputForXorXnor(currentNodeInfo,
                       curInput,
                       breakInput):
    inputs = currentNodeInfo[0]['node']['inputs']

    currentInput = curInput

    zeroFound = "false"
    oneFound = "false"

    for binaryNum in inputs:
        if binaryNum == 1:
            oneFound = "true"
        elif binaryNum == 0:
            zeroFound = "true"

        if oneFound == "true" and zeroFound == "true":
            currentInput = breakInput
            break

    return currentInput


# def constructBinaryDecisionDiagram(graph,
#                                    inputsProcessedOrder,
#                                    currentCombination,
#                                    output,
#                                    combinationLoopCount,
#                                    bddNodeKey):
#
#     inputs = inputsProcessedOrder.split(',')
#
#     inputKeyList = []
#
#     currentInputKeyIndex = 0
#
#     if combinationLoopCount == 0:
#         for input in inputs:
#             # graph.run("CREATE (:TBDD {label:{from}})-[:<<binaryNum>>]->(:TBDD {label:{to}})", from=input, binaryNum=, to=)
#             createBDDNode(bddNodeKey, input)
#             inputKeyList.append(bddNodeKey)
#             bddNodeKey = bddNodeKey + 1
#
#         createBDDNode(bddNodeKey, output[0])
#         inputKeyList.append(bddNodeKey)
#         bddNodeKey = bddNodeKey + 1
#
#         while not currentInputKeyIndex == (len(inputKeyList) - 1):
#             if currentCombination[currentInputKeyIndex] == 0:
#                 relationLabel = "zero"
#             else:
#                 relationLabel = "one"
#
#             createBDDRelationship(inputKeyList[currentInputKeyIndex], inputKeyList[currentInputKeyIndex + 1],
#                                   relationLabel)
#             currentInputKeyIndex = currentInputKeyIndex + 1
#     else:
#         inputKeyList = inputs + output
#
#         firstLinkChildNode = graph.data(
#             "MATCH (parent:TBDD)-[rel:{relationLbl}]->(child:TBDD) WHERE parent.inputLabel= {inputLabel} RETURN child",
#             parameters={"rel": currentCombination[currentInputKeyIndex], "inputLabel": inputs[currentInputKeyIndex]})
#         currentInputKeyIndex = currentInputKeyIndex + 1
#
#         previousKey = firstLinkChildNode[0]['child']['key']
#
#         if firstLinkChildNode:
#             while not currentInputKeyIndex == (len(inputKeyList) - 1):
#                 nextLinkChildNode = graph.data(
#                     "MATCH (parent:TBDD)-[rel:{relationLbl}]->(child:TBDD) WHERE parent.inputLabel= {inputLabel} RETURN child",
#                     parameters={"rel": currentCombination[currentInputKeyIndex], "inputLabel": previousKey})
#
#                 if not nextLinkChildNode:
#                     # if
#                     createBDDNode(bddNodeKey, inputs[currentInputKeyIndex + 1])
#                     bddNodeKey = bddNodeKey + 1
#
#                     if currentCombination[currentInputKeyIndex] == 0:
#                         relationLabel = "zero"
#                     else:
#                         relationLabel = "one"
#
#                     createBDDRelationship(previousKey, bddNodeKey-1, relationLabel)
#
#                     previousKey = nextLinkChildNode[0]['child']['key']
#                     currentInputKeyIndex = currentInputKeyIndex + 1
#                     continue
#                 else:
#                     previousKey = nextLinkChildNode[0]['child']['key']
#
#                 currentInputKeyIndex = currentInputKeyIndex + 1
#
#
#     inputKeyList = []
#
#     return bddNodeKey



def simulateLogicGate(diagramBelongsTo, noOfInputs, logicGateQuestionId):
    # Connect to Graph
    graph = connectToGraph()

    # noOfInputs = resultSet[0]
    binaryCombinationList = list(itertools.product([0, 1], repeat=noOfInputs))

    print(binaryCombinationList)

    queue = []

    inputsProcessedOrder = ''

    noOfMatchedCombinations = 0

    bddNodeKey = 1

    inputNodes = graph.data(
        "MATCH (node:%s) WHERE node.symbol='input' RETURN node" % diagramBelongsTo)

    if diagramBelongsTo == "Teacher":
        count = 0
        while count < len(inputNodes):
            queue.insert(0, inputNodes[count]['node']['key'])
            count = count + 1

    elif diagramBelongsTo == "Student":
        connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword, db=mySQLdatabase)
        cur = connection.cursor()
        cur.execute("SELECT inputProcessedOrder FROM logic_gate_question WHERE logicgateqId = %s", (logicGateQuestionId))
        resultSet = cur.fetchone()
        cur.close()
        connection.close()

        inputsProcessedOrder = resultSet[0]


    print(binaryCombinationList[0])
    # currentCombination = binaryCombinationList[1]
    # print(binaryCombinationList[1][2])

    combinationLoopCount = 0
    while combinationLoopCount < len(binaryCombinationList):

        inputsProcessedCount = 0

        print('Inside combination while loop')
        currentCombination = binaryCombinationList[combinationLoopCount]

        if diagramBelongsTo == "Student" or (combinationLoopCount >= 1 and diagramBelongsTo == "Teacher"):
            inputs = inputsProcessedOrder.split(',')
            print('for the rest of the combinations')
            print(inputs)

            for input in inputs:
                count = 0
                while count < len(inputNodes):
                    if inputNodes[count]['node']['text'] == input:
                        queue.insert(0, inputNodes[count]['node']['key'])
                        break
                    count = count + 1

        while queue:
            currentNode = queue.pop()

            print('current node')
            print(currentNode)

            currentNodeInfo = graph.data(
                "MATCH (node:%s) WHERE node.key= {key} RETURN node" % diagramBelongsTo,
                parameters={"key": currentNode})

            currentChildNodes = graph.data(
                "MATCH (parent:%s)-[:TO]->(child:%s) WHERE parent.key= {key} RETURN child" % (diagramBelongsTo, diagramBelongsTo),
                parameters={"key": currentNode})

            if currentNodeInfo[0]['node']['symbol'] == "input" and combinationLoopCount == 0 and diagramBelongsTo == "Teacher":
                inputsProcessedOrder = inputsProcessedOrder + currentNodeInfo[0]['node']['text'] + ","

            if currentNodeInfo[0]['node']['symbol'] == "input":
                currentInput = currentCombination[inputsProcessedCount]
                inputsProcessedCount = inputsProcessedCount + 1


            # print(currentChildNodes)
            print(currentInput)

            if currentNodeInfo[0]['node']['symbol'] == "output":
                print('OUTPUT:')
                if combinationLoopCount == 0 and diagramBelongsTo == "Teacher":
                    inputsProcessedOrder = inputsProcessedOrder[:-1]
                print(inputsProcessedOrder)
                print(currentCombination)
                print(currentNodeInfo[0]['node']['inputs'])

                output = currentNodeInfo[0]['node']['inputs']

                graph.run("MATCH (node:%s) REMOVE node.inputs" % diagramBelongsTo)

                # bddNodeKey = constructBinaryDecisionDiagram(graph, inputsProcessedOrder, currentCombination,
                #                                currentNodeInfo[0]['node']['inputs'], combinationLoopCount,
                #                                bddNodeKey)

                if diagramBelongsTo == "Teacher":
                    connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword,
                                                 db=mySQLdatabase)
                    cur = connection.cursor()
                    if noOfInputs == 1:
                        cur.execute("INSERT INTO simulate_logicgate(inputOne, output) VALUES('%s', '%s')", (currentCombination[0], output[0]))
                    elif noOfInputs == 2:
                        cur.execute("INSERT INTO simulate_logicgate(inputOne, inputTwo, output) VALUES('%s', '%s', '%s')",
                                    (currentCombination[0], currentCombination[1], output[0]))
                    elif noOfInputs == 3:
                        cur.execute("INSERT INTO simulate_logicgate(inputOne, inputTwo, inputThree, output) VALUES('%s', '%s', '%s', '%s')",
                                    (currentCombination[0], currentCombination[1], currentCombination[2], output[0]))
                    cur.close()
                    connection.close()
                elif diagramBelongsTo == "Student":
                    connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword,
                                                 db=mySQLdatabase)
                    cur = connection.cursor()
                    if noOfInputs == 1:
                        cur.execute("SELECT output FROM simulate_logicgate WHERE inputOne = '%s'", (currentCombination[0]))
                    elif noOfInputs == 2:
                        cur.execute("SELECT output FROM simulate_logicgate WHERE inputOne = '%s' AND inputTwo = '%s'",
                                    (currentCombination[0], currentCombination[1]))
                    elif noOfInputs == 3:
                        cur.execute("SELECT output FROM simulate_logicgate WHERE inputOne = '%s' AND inputTwo = '%s' AND inputThree = '%s'",
                                    (currentCombination[0], currentCombination[1], currentCombination[2]))
                    resultSet = cur.fetchone()
                    cur.close()
                    connection.close()

                    if resultSet[0] == output[0]:
                        print('^^^^^^^^^^^^^^^^^^retrieved output and simulated output equal')
                        noOfMatchedCombinations = noOfMatchedCombinations + 1


            for childNode in currentChildNodes:
                childParents = graph.data(
                    "MATCH (parent:%s)-[:TO]->(child:%s) WHERE child.key= {key} RETURN parent" % (diagramBelongsTo, diagramBelongsTo),
                    parameters={"key": childNode['child']['key']})

                childNodeDetails = Node(diagramBelongsTo, key=childNode['child']['key'])
                print(childNodeDetails)
                graph.merge(childNodeDetails)

                if currentNodeInfo[0]['node']['symbol'] == "input":
                    print('^^^INPUT')
                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "and":
                    print('^^^AND')

                    currentInput = getInputForAndOrNandNor(currentNodeInfo, 1, 0, 0)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "or":
                    print('^^^OR')

                    currentInput = getInputForAndOrNandNor(currentNodeInfo, 0, 1, 1)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "not":
                    inputs = currentNodeInfo[0]['node']['inputs']
                    print('^^^NOT')
                    print(inputs[0])

                    if inputs[0] == 0:
                        print('current input is ZERO')
                        currentInput = 1
                    else:
                        print('current input is ONE')
                        currentInput = 0

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "nand":
                    print('^^^NAND')

                    currentInput = getInputForAndOrNandNor(currentNodeInfo, 0, 0, 1)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "nor":
                    print('^^^NOR')

                    currentInput = getInputForAndOrNandNor(currentNodeInfo, 1, 1, 0)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "xor":
                    print('^^^XOR')

                    currentInput = getInputForXorXnor(currentNodeInfo, 0, 1)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "xnor":
                    print('^^^XNOR')

                    currentInput = getInputForXorXnor(currentNodeInfo, 1, 0)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)


                childNodeDetails.push()


        if diagramBelongsTo == "Teacher":
            connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword,
                                         db=mySQLdatabase)
            cur = connection.cursor()
            cur.execute("UPDATE logic_gate_question SET inputProcessedOrder = %s WHERE logicgateqId = %s",
                        (inputsProcessedOrder, logicGateQuestionId))
            cur.close()
            connection.close()

        print('incrementing combinationLoopCount by 1')
        combinationLoopCount = combinationLoopCount + 1

        print('no of matched combintions')
        print(noOfMatchedCombinations)

    return noOfMatchedCombinations

# simulateLogicGate("Teacher")
# simulateLogicGate("Student")

def deleteSimulationCombinationData():
    connection = pymysql.connect(host=mySQLhostname, user=mySQLusername, passwd=mySQLpassword,
                                 db=mySQLdatabase)
    cur = connection.cursor()
    cur.execute("DELETE FROM simulate_logicgate")
    cur.close()
    connection.close()

# deleteSimulationCombinationData()