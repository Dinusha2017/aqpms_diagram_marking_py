import pymysql

import itertools

from py2neo import Node

from CreateGraph import connectToGraph

from DbConnection import connectToMySQL


def handleGateInputsAndQueue(childNode,
                             childNodeDetails,
                             currentInput,
                             childParents,
                             queue):
    if not childNode['child']['inputs']:
        childNodeDetails['inputs'] = [currentInput]

        if len(childParents) == 1:
            queue.insert(0, childNode['child']['key'])
    else:
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


def simulateLogicGate(diagramBelongsTo, noOfInputs, logicGateQuestionId):
    # Connect to Graph
    graph = connectToGraph()

    # noOfInputs = resultSet[0]
    binaryCombinationList = list(itertools.product([0, 1], repeat=noOfInputs))

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
        connection = connectToMySQL()
        cur = connection.cursor()
        cur.execute("SELECT inputProcessedOrder FROM logic_gate_question WHERE logicgateqId = %s", (logicGateQuestionId))
        resultSet = cur.fetchone()
        cur.close()
        connection.close()

        inputsProcessedOrder = resultSet[0]

    combinationLoopCount = 0
    while combinationLoopCount < len(binaryCombinationList):

        inputsProcessedCount = 0

        currentCombination = binaryCombinationList[combinationLoopCount]

        if diagramBelongsTo == "Student" or (combinationLoopCount >= 1 and diagramBelongsTo == "Teacher"):
            inputs = inputsProcessedOrder.split(',')
           
            for input in inputs:
                count = 0
                while count < len(inputNodes):
                    if inputNodes[count]['node']['text'] == input:
                        queue.insert(0, inputNodes[count]['node']['key'])
                        break
                    count = count + 1

        while queue:
            currentNode = queue.pop()

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

            if currentNodeInfo[0]['node']['symbol'] == "output":
                if combinationLoopCount == 0 and diagramBelongsTo == "Teacher":
                    inputsProcessedOrder = inputsProcessedOrder[:-1]
                output = currentNodeInfo[0]['node']['inputs']

                graph.run("MATCH (node:%s) REMOVE node.inputs" % diagramBelongsTo)

                if diagramBelongsTo == "Teacher":
                    connection = connectToMySQL()
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
                    connection = connectToMySQL()
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
                        noOfMatchedCombinations = noOfMatchedCombinations + 1


            for childNode in currentChildNodes:
                childParents = graph.data(
                    "MATCH (parent:%s)-[:TO]->(child:%s) WHERE child.key= {key} RETURN parent" % (diagramBelongsTo, diagramBelongsTo),
                    parameters={"key": childNode['child']['key']})

                childNodeDetails = Node(diagramBelongsTo, key=childNode['child']['key'])
                graph.merge(childNodeDetails)

                if currentNodeInfo[0]['node']['symbol'] == "input":
                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "and":
                    currentInput = getInputForAndOrNandNor(currentNodeInfo, 1, 0, 0)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "or":
                    currentInput = getInputForAndOrNandNor(currentNodeInfo, 0, 1, 1)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "not":
                    inputs = currentNodeInfo[0]['node']['inputs']

                    if inputs[0] == 0:
                        currentInput = 1
                    else:
                        currentInput = 0

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "nand":
                    currentInput = getInputForAndOrNandNor(currentNodeInfo, 0, 0, 1)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "nor":
                    currentInput = getInputForAndOrNandNor(currentNodeInfo, 1, 1, 0)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "xor":
                    currentInput = getInputForXorXnor(currentNodeInfo, 0, 1)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)
                elif currentNodeInfo[0]['node']['symbol'] == "xnor":
                    currentInput = getInputForXorXnor(currentNodeInfo, 1, 0)

                    handleGateInputsAndQueue(childNode, childNodeDetails, currentInput, childParents, queue)

                childNodeDetails.push()


        if diagramBelongsTo == "Teacher":
            connection = connectToMySQL()
            cur = connection.cursor()
            cur.execute("UPDATE logic_gate_question SET inputProcessedOrder = %s WHERE logicgateqId = %s",
                        (inputsProcessedOrder, logicGateQuestionId))
            cur.close()
            connection.close()

        combinationLoopCount = combinationLoopCount + 1

    return noOfMatchedCombinations

def deleteSimulationCombinationData():
    connection = connectToMySQL()
    cur = connection.cursor()
    cur.execute("DELETE FROM simulate_logicgate")
    cur.close()
    connection.close()