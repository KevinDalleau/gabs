import rdflib
import time
import numpy as np
from skbio.stats.distance import mantel


def loadIndividuals(graph):
    queryString = "SELECT ?individuals ?individualId WHERE {?individuals <http://www.graph.com/nodeType/>  \"individual\" . ?individuals <http://graph.com/identifier> ?individualId.}"
    res = graph.query(queryString)
    output = {}
    for row in res:
        name =  str(row[0]).replace("http://graph.com/individual/","")
        indId = int(row[1])
        output[name] = indId
    return output

def loadAttributes(graph,offset):
    queryString = "SELECT ?attributes WHERE {?attributes <http://www.graph.com/nodeType/>  \"attribute\".}"
    res = graph.query(queryString)
    output = {}
    i=1
    for row in res:
        name = str(row[0]).replace("http://graph.com/","")
        output[name] = i+offset
        i+=1
    return output

def getSparseGraph(graph, individuals, attributes):
    queryString = "SELECT DISTINCT ?individual ?attribute WHERE {?individual <http://www.graph.com/nodeType/> \"individual\". ?individual <http://graph.com/relation/linked> ?attribute. ?attribute <http://www.graph.com/nodeType/> \"attribute\"}"
    res= graph.query(queryString)
    output = {}
    for row in res:
        individualName = str(row[0]).replace("http://graph.com/individual/","")
        attributeName = str(row[1]).replace("http://graph.com/","")
        individualIndex = individuals[individualName]
        attributeIndex = attributes[attributeName]
        if individualIndex not in output:
            output[individualIndex] = set()
        if attributeIndex not in output:
            output[attributeIndex] = set()
        output[individualIndex].add(attributeIndex)
        output[attributeIndex].add(individualIndex)

    queryString = "SELECT DISTINCT ?attribute1 ?commonAttribute WHERE { ?attribute1 <http://www.graph.com/nodeType/> \"attribute\". ?commonAttribute <http://www.graph.com/nodeType/> \"attribute\". ?attribute1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?commonAttribute.}"
    res= graph.query(queryString)
    for row in res:
        attributeName = str(row[0]).replace("http://graph.com/","")
        commonAttributeName = str(row[1]).replace("http://graph.com/","")
        attributeIndex = attributes[attributeName]
        commonAttributeIndex = attributes[commonAttributeName]
        if attributeIndex not in output:
            output[attributeIndex] = set()
        if commonAttributeIndex not in output:
            output[commonAttributeIndex] = set()
        output[attributeIndex].add(commonAttributeIndex)
        output[commonAttributeIndex].add(attributeIndex)


    return output

def getSymetric(matrix):
    n = len(matrix)
    for i in range(0,n):
        for j in range(0,i):
            matrix[i][j] = matrix[j][i]
    return matrix


def getChildren(parentsLists,matrix,grandParentsLists):
    output = []
    while parentsLists:
        subOutput = []
        parentList = parentsLists.pop(0)
        grandParentList = grandParentsLists.pop(0)
        while parentList:
            parent = parentList.pop(0)
            children = list(matrix[parent])
            children.remove(grandParentList)
            subOutput.append(children)
        output.extend(subOutput)
    return output


def customProduct(kMult, matrix, attributes,avoidMemory):
    n = len(kMult)
    output = [[0]*n for x in range(n)]
    for row in range(0,n):
        for col in range(0,n):
            value = 0
            if (row-1) not in attributes and (col-1) not in attributes:
                if col > row:
                    for k in attributes:
                        localValue = kMult[row][k-1]*matrix[k-1][col]
                        if localValue >=1:
                            value += localValue
                else:
                    value = output[col][row]
            else:
                if avoidMemory[row][col] == 0:
                    if col>row:
                        for k in attributes:
                            localValue = kMult[row][k-1]*matrix[k-1][col]
                            if localValue >=1:
                                value += localValue
            output[row][col] = value

    return output

def customProductNaive(a, b, attributes):
    m=len(a)
    n=len(a[0])
    k=len(b)
    res=[]
    if len(b) != 1:
            p=len(b[0])-1
    else:
            p=0
    if len(b)==0:
        print('bad size')
    elif n!=k:
        print('bad size')
    else:
        n=k
        for q in range(m):
		res.append([0])
        for q in range(m):
		for w in range(p):
			res[q].append(0)
        for i in range(m):
            for j in range(p+1):
			for k in attributes:
				res[i][j] += a[i][k-1]*b[k-1][j]
    return res

def customPowerNaive(matrix,power,attributes):
    output = matrix
    for i in range(2,power+1):
        output = customProductNaive(output,matrix,attributes)
    return output

def product(a,b):
    m=len(a)
    n=len(a[0])
    k=len(b)
    res=[]
    if len(b) != 1:
            p=len(b[0])-1
    else:
            p=0
    if len(b)==0:
        print('bad size')
    elif n!=k:
        print('bad size')
    else:
        n=k
        for q in range(m):
		res.append([0])
        for q in range(m):
		for w in range(p):
			res[q].append(0)
        for i in range(m):
            for j in range(p+1):
			for k in range(k):
				res[i][j] += a[i][k-1]*b[k-1][j]
    return res

def aggregatePaths(matrix, individuals, attributes, depth):
    n = len(individuals)
    output = [[0]*n for x in range(0,n)]
    kMult = matrix
    avoidMemory = matrix
    avoidMemory2 = matrix
    oldMatrix = list()
    for it in range(2,depth+1):
        oldMatrix = output
        avoidMemory = avoidMemory2
        avoidMemory2 = kMult
        if it <= 3:
            kMult = customProduct(kMult, matrix, attributes, matrix)
        else:
            kMult = customProduct(kMult, matrix, attributes, avoidMemory)
        #print kMult
        for i in range(0, n):
            for j in range(0,n):
                if j >= i:
                    valueAtDepth = kMult[individuals[i]-1][individuals[j]-1]
                    if valueAtDepth >= 1 and i != j:
                        oldValue = oldMatrix[i][j]
                        output[i][j] = float(oldValue) + float(valueAtDepth)/it
                else:
                    output[i][j] = output[j][i]
    return output

def aggregateWalks(matrix, individuals, attributes):
    n = len(individuals)
    output = [[0]*n for x in range(0,n)]
    kMult = matrix
    oldMatrix = list()
    for it in range(2,5):
        oldMatrix = output

        kMult = customPowerNaive(matrix, it, attributes)

        #print kMult
        for i in range(0, n):
            for j in range(0,n):
                if j >= i:
                    valueAtDepth = kMult[individuals[i]-1][individuals[j]-1]
                    if valueAtDepth >= 1 and i != j:
                        oldValue = oldMatrix[i][j]
                        output[i][j] = float(oldValue) + float(valueAtDepth)/it
                else:
                    output[i][j] = output[j][i]
    return output

def sparseToDense(sparse,individuals,attributes):
    n = len(individuals)+len(attributes)

    output = [[0]*n for x in range(0,n)]

    for key in sparse.keys():
        values = sparse[key]
        for value in values:
            output[key-1][value-1] = 1
            output[value-1][key-1] = 1
    return output

def sparseToTransition(sparse,individuals,attributes):
    n = len(individuals)+len(attributes)
    output = [[0]*n for x in range(0,n)]

    for key in sparse.keys():
        values = sparse[key]
        for value in values:
            output[key-1][value-1] = float(1)/len(values)
    return output

graph = rdflib.Graph()
graph.load("./data/output_actors.rdf", format="nt")
individualsDict = loadIndividuals(graph)
print individualsDict
individualsSet = set(sorted(individualsDict.values()))

offset = len(individualsDict)
attributesDict = loadAttributes(graph,offset)
sparse = getSparseGraph(graph,individualsDict,attributesDict)
dense = sparseToDense(sparse, individualsSet,set(attributesDict))


start_time = time.time()
resultAgg1 = aggregatePaths(dense,list(individualsSet),list(sorted(attributesDict.values())),4)
print("--- %s seconds --- GABSPaths" % (time.time() - start_time))

start_time = time.time()
resultKatz1 = np.array(aggregateWalks(dense,list(individualsSet),list(sorted(attributesDict.values()))))
print("--- %s seconds --- GABSWalks" % (time.time() - start_time))

np.savetxt("actorsagg.csv",np.asarray(resultAgg1),delimiter=",")

print mantel(resultAgg1,resultKatz1)
