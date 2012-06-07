from analysis import *
import copy
from surface import *
from itertools import permutations
import numpy
from gcd import gcd

def returnList():
	# incorporate x, y, z symmetries

    indices = []
    sizes = []

    for h in range(1,40):
        for k in range(0,40):
            for l in range(0,40):
                if (abs(gcd(gcd(h,k),gcd(k,l)))==1) or (abs(gcd(gcd(h,k),gcd(k,l)))==0) and not h+k+l==0:
                    new_index = [h,k,l]
                    indices.append(new_index)
                    surf=makeSurface('Pt','fcc', new_index,size=(1,1,5))
                    volume = abs(np.dot(np.cross(surf.get_cell()[0],surf.get_cell()[1]),surf.get_cell()[2]))
                    sizes.append(volume)

    return indices, sizes 

	# plot the points on a sphere to see where they lie?

def checkForSameEnergies(fileName, tol=1e-7):
	indices, e_unrelaxed, e_relaxed, size = loadFileIntoLists(fileName)
	e_relaxed_copy = copy.copy(e_relaxed)
	dict_multiples={}
	for i in range(0,len(e_relaxed)):
		energy = e_relaxed[i]
		dict_multiples[energy]=[indices[i]]
		for energy2 in e_relaxed_copy:
			if energy2<=energy+tol and energy2>=energy-tol:
				curr_index = e_relaxed.index(energy2)
				e_relaxed_copy.pop(e_relaxed_copy.index(energy2))
				dict_multiples[energy].append(indices[curr_index])
	
	for key in dict_multiples.keys():
		if len(dict_multiples[key])==2:
			if dict_multiples[key][0]==dict_multiples[key][1]:
				dict_multiples.pop(key)
		elif len(dict_multiples[key])==1:
			dict_multiples.pop(key)

	return dict_multiples
				
				
def generateEvenlySampledIndices(N):
    """
    more or less uniformly sample a sphere
    make indices from function pointsOnSphere
    """ 
    pts = pointsOnSphere(N)
    indices = []
    sizes = []
    for vector in pts:
        miller = copy.copy(vector)
        minCoor = min(vector)
        miller = numpy.array(miller)/minCoor
        # make all of these integers
        miller = [int(miller[0]), int(miller[1]), int(miller[2])]
        indices.append(miller)
        surf=makeSurface('Pt','fcc', miller,size=(1,1,5)) 
        volume = abs(np.dot(np.cross(surf.get_cell()[0],surf.get_cell()[1]),surf.get_cell()[2]))
        sizes.append(volume)

    return indices, sizes 

def pointsOnSphere(N):
    """
    this returns evenly distributed points on a sphere
    """

    N = float(N) # in case we got an int which we surely got
    pts = []
 
    inc = numpy.pi * (3 - numpy.sqrt(5))
    off = 2 / N
    for k in range(0, int(N)):
        y = k * off - 1 + (off / 2)
        r = numpy.sqrt(1 - y*y)
        phi = k * inc
        pts.append([numpy.cos(phi)*r, y, numpy.sin(phi)*r])
 
    return pts				

def pruneIndexList(indexList, sizes, volume_cutoff):
    """
    get rid of repeating indices due to symmetries, and also ones that have too large cell sizes... make indices all positive cause it will be that quadrant..
    """
    new_list = []
    existing_miller_indices = []
    new_sizes = []
    for i in range(0,len(indexList)):
        miller = indexList[i]
        miller = [abs(miller[0]),abs(miller[1]),abs(miller[2])]
        volume = sizes[i]
        if volume <= volume_cutoff:
            if miller not in existing_miller_indices: 
                new_list.append(miller)
                permuted_indices = [list(a) for a in permutations(miller)]
                existing_miller_indices += permuted_indices
                new_sizes.append(volume)   
 
    return new_list, new_sizes

def getIndexList(N, volume_cutoff=5000):

    indices, sizes = returnList()
    new_list, new_sizes = pruneIndexList(indices,sizes,volume_cutoff)
    sorted_sizes = sorted(new_sizes)
    selected_list=[]
    selected_sizes=[]
    # sizes that are close to one another will be close too in space?
    # pick the important surfaces, then populate others randomnly?
    for size in sorted_sizes[0:N]:
        selected_list.append(new_list[new_sizes.index(size)]) 
        selected_sizes.append(size)
    return selected_list,selected_sizes

def loadIndexList(fileName):
    file = open(fileName)
    list, sizes = pickle.load(file)
    file.close()
    
    return list,sizes
