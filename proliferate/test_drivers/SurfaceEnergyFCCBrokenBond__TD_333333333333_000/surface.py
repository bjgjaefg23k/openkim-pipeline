import ase
import ase.lattice
import ase.lattice.cubic
from ase import *
from ase.optimize import FIRE, BFGS
import numpy as np
from numpy.linalg import norm, solve
from gcd import gcd
import kimcalculator

def makeSurface(symbol,structure,indices,size=(1,1,1),tol=1e-10):
	"""
	this function makes the surface and also identical bulk structure with atoms
	symbol: what type of atom, in a string
	structure: currently supported fcc, bcc, hcp, diamond
	indices: miller index of the surface
	size: tuple of (s_x,s_y,s_z) to use for the box
	"""
	
	# first decide which function we want to use to build the structure
	if structure=='fcc':
		atoms_fn = getattr(ase.lattice.cubic,'FaceCenteredCubic')
	elif structure=='bcc':
		atoms_fn = getattr(ase.lattice.cubic,'BodyCenteredCubic')
	elif structure=='hcp':
		atoms_fn = getattr(ase.lattice.hexagonal, 'HexagonalClosedPacked')
	elif structure=='diamond':
		atoms_fn = getattr(ase.lattice.cubic,'Diamond')
	else:
		print "structure defined not supported"
		raise Exception
		
	h , k , l = indices
	miller = [None,None,[h,k,l]] # put in this argument as internal check
	lattice = atoms_fn(symbol)
	# problem, should specify miller at the same time as directions	

	# now calculate the vectors to put along x,y,z directions
	
	a1, a2, a3 = lattice.cell 
		
	h0, k0, l0 = (h == 0,k==0,l==0)
	if h0 and k0 or h0 and l0 or k0 and l0:  # if two indices are zero
		if not h0:
			c1, c2, c3 = [(0, 1, 0), (0, 0, 1), (1, 0, 0)]
		if not k0:
			c1, c2, c3 = [(1, 0, 0), (0, 0, 1), (0, 1, 0)]
		if not l0:
			c1, c2, c3 = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
	else:
		p, q = ext_gcd(k, l)
		a1, a2, a3 = lattice.cell # this is the lattice constants

        # constants describing the dot product of basis c1 and c2:
        # dot(c1,c2) = k1+i*k2, i in Z
		k1 = np.dot(p * (k * a1 - h * a2) + q * (l * a1 - h * a3), l * a2 - k * a3)
		k2 = np.dot(l * (k * a1 - h * a2) - k * (l * a1 - h * a3), l * a2 - k * a3)
		if abs(k2) > tol:
			i = -int(round(k1 / k2))  # i corresponding to the optimal basis
			p, q = p + i * l, q - i * k

		a, b = ext_gcd(p * k + q * l, h)

		c1 = (p * k + q * l, -p * h, -q * h)
		c2 = np.array((0, l, -k)) // abs(gcd(l, k))
		c3 = (b, a * p, a * q)

	# layers wanted in surface direction
	# along each surface direction, the number of atoms are different
	# have to first determine that

	
	layers=size[2]
	d_v3 = max(int(1.0*layers/(np.dot(np.array(c3),indices/norm(indices)))),1)	

	size_to_build = (size[0],size[1],d_v3)

	surface = build(lattice, np.array([c1,c2,c3]),size_to_build,tol)

	return surface

def build(lattice, basis, size, tol):
	"""
	to build lattice structure, can make surface or bulk depending on pbc
	"""
	surf = lattice.copy()
	scaled = solve(basis.T, surf.get_scaled_positions().T).T
	scaled -= np.floor(scaled + tol)
	surf.set_scaled_positions(scaled)
	surf.set_cell(np.dot(basis, surf.cell), scale_atoms=True)
	
	surf *= size

	# why do this first?
	a1, a2, a3 = surf.cell
	surf.set_cell([a1, a2, \
                   np.cross(a1, a2) * np.dot(a3, np.cross(a1, a2)) /\
                   norm(np.cross(a1, a2))**2])

    	# Change unit cell to have the x-axis parallel with a surface vector
    	# and z perpendicular to the surface:
	a1, a2, a3 = surf.cell

	surf.set_cell([(norm(a1), 0, 0), \
                   (np.dot(a1, a2) / norm(a1), \
                    np.sqrt(norm(a2)**2 - (np.dot(a1, a2) / norm(a1))**2), 0), \
                   (0, 0, -norm(a3))], \
                  scale_atoms=True)	

	surf.pbc = (True, True, False)
	
    	# Move atoms into the unit cell:
	scaled = surf.get_scaled_positions()
	scaled[:, :2] %= 1
	surf.set_scaled_positions(scaled)

	return surf


def surface_energy(surface, calc, accuracy=0.00001, shake=0.1, seed=1):
	"""
	calculates the energy of the surface (without dividing by the area or subtracting bulk)
	Note: we will calculate the bulk energy for one atom and multiply by number of atoms to save time in calculation
	"""

	symbol = surface.get_chemical_symbols()[0]
	
	a = 3.92
	surface.set_calculator(calc)

	e_surface = surface.get_potential_energy()

	# rattle surface atoms a bit, to relax, get relaxed energy
	surface.rattle(stdev=shake,seed=seed)
	dyn = FIRE(surface)
	dyn.run(fmax=accuracy)
	e_relaxed_surface =  surface.get_potential_energy()

	return e_surface, e_relaxed_surface


def ext_gcd(a, b):
    if b == 0:
        return 1, 0
    elif a % b == 0:
        return 0, 1
    else:
        x, y = ext_gcd(b, a % b)
        return y, x - y * (a / b)

