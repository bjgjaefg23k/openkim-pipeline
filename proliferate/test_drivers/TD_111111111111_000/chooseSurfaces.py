import copy
from surface import *
from itertools import permutations
import numpy

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
    for i in range(0,len(indexList)):
        miller = indexList[i]
        miller = [abs(miller[0]),abs(miller[1]),abs(miller[2])]
        volume = sizes[i]
        if volume <= volume_cutoff:
            if miller not in existing_miller_indices: 
                new_list.append(miller)
                permuted_indices = [list(a) for a in permutations(miller)]
                existing_miller_indices += permuted_indices
    
    return new_list

def getIndexList(N, volume_cutoff=5000):

    indices, sizes = generateEvenlySampledIndices(N)
    new_list = pruneIndexList(indices,sizes,volume_cutoff)

    return new_list
