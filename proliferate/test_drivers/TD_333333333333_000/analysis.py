import numpy
import pylab
pylab.ioff()
from numpy import sin, cos, pi
from scipy.optimize import leastsq
import scipy.optimize
from ase.lattice.cubic import FaceCenteredCubic
from ase import Atoms
from enthought.mayavi.mlab import *
from scipy.special import sph_harm

# this is to analyze the surface energies

def energyVsAngle(file,index0,poleaxis):
	"""
	plots calculated surfaces choosing family of planes perpendicular to index0, and as function of angle to poleaxis
	"""

	f = open(file,'r')

	for line in f.readlines()[3:]:
		index, e_unrelaxed, e_relaxed, cell_size = line.split('\t')
		print cell_size
		e_unrelaxed = float(e_unrelaxed)
		e_relaxed = float(e_relaxed)
		h = int(index.split(',')[0].strip('['))
		k = int(index.split(',')[1])
		l = int(index.split(',')[2].strip(']'))
		index = [h,k,l]
		if numpy.dot(index,index0)==0:			
			angle = 2.**numpy.arccos(numpy.dot(poleaxis,[h,k,l])/(numpy.sqrt((h**2+k**2+l**2)*numpy.dot(poleaxis,poleaxis))))*180/numpy.pi
			pylab.plot(angle,e_unrelaxed,'r.')
			pylab.plot(angle,e_relaxed,'g.')

	fileNameHeader = file.split('.')[0] + 'index_'+str(index0)

	pylab.savefig(fileNameHeader+'plot.png')

	#pylab.show()

def negativeEnergySurface(file):
	"""
	returns which surfaces are negative in energy as a list
	""" 
	surfaces = []
	
	f = open(file,'r')

	for line in f.readlines()[3:]:
		index, e_unrelaxed, e_relaxed, cell_size = line.split()
		e_unrelaxed = float(e_unrelaxed)
		e_relaxed = float(e_relaxed)
		h = int(index.split(',')[0].strip('['))
		k = int(index.split(',')[1])
		l = int(index.split(',')[2].strip(']'))
		index = [h,k,l]

		if e_unrelaxed > 0 and e_relaxed >0:
			surfaces.append(index)

	f.close()

	return surfaces

def angles(h,k,l):
	
	if h is not 0:
		phi = pylab.arctan2(k,h)*180/numpy.pi
	elif k<0:
		phi = -90
	elif k>0:
		phi = 90
	elif k==0:
		phi = 0

	theta = numpy.arccos(l/numpy.sqrt(h**2+k**2+l**2))*180/numpy.pi

	return phi, theta

def radianangles(h,k,l):
	phidegrees, thetadegrees = angles(h,k,l)

	return phidegrees/180.*numpy.pi, thetadegrees/180.*numpy.pi

def thetaphis(nvector):

	phi_list = []
	theta_list = []

	if isinstance(nvector,list):
		shaperows=1
		if isinstance(nvector[0],list): # in case this is a nested list
			shaperows = len(nvector)	
	elif isinstance(nvector, numpy.ndarray):
		shaperows = nvector.shape[0]
	
	if shaperows ==1:
		[h,k,l] = nvector
		phi, theta = angles(h,k,l)
		return phi, theta	
	elif shaperows > 1:
		for row in range(0,shaperows):
			[h,k,l] = nvector[row]
			phi, theta = angles(h,k,l)
			phi_list.append(phi)
			theta_list.append(theta)
	
		return phi_list, theta_list


def listofangles(file,index0,poleaxis):
	
	f = open(file,'r')
	newfile = file.split('.')[0]+str(index0)+'angles.txt'
	g = open(newfile,'w')

	h = poleaxis[0]
	k = poleaxis[1]
	l = poleaxis[2]

	print poleaxis

	#phi0, theta0 = angles(h,k,l)

	for line in f.readlines()[3:]:
		index, e_unrelaxed, e_relaxed, cell_size = line.split()
		h = int(index.split(',')[0].strip('['))
		k = int(index.split(',')[1])
		l = int(index.split(',')[2].strip(']'))

		if numpy.dot([h,k,l],index0)==0:
			#phi, theta = angles(h,k,l)
			#phi0,theta0 = angles(,1,0)

			#angle = numpy.arccos(sin(theta)*sin(theta0)*cos(phi-phi0)+cos(theta)*cos(theta0))*180/numpy.pi
			angle = numpy.arccos(numpy.dot(poleaxis,[h,k,l])/(numpy.sqrt((h**2+k**2+l**2)*numpy.dot(poleaxis,poleaxis))))*180/numpy.pi
			
			g.write(str(index)+'\t'+str(angle)+'\n')

	f.close()
	g.close()


def loadFileIntoLists(fileName):

	f=open(fileName,'r')

	indices = []
	unrel_es = []
	rel_es = []
	sizes = []

	for line in f.readlines()[3:]:
		index, e_unrelaxed, e_relaxed, cell_size = line.split()
		e_unrelaxed = float(e_unrelaxed)
		e_relaxed = float(e_relaxed)
		h = int(index.split(',')[0].strip('['))
		k = int(index.split(',')[1])
		l = int(index.split(',')[2].strip(']'))
		indices.append([h,k,l])
		unrel_es.append(e_unrelaxed)
		rel_es.append(e_relaxed)
		x = int(cell_size.split(',')[0].strip('('))
		y = int(cell_size.split(',')[1])
		z = int(cell_size.split(',')[2].strip(')\n'))
		sizes.append((x,y,z))

	return indices, unrel_es, rel_es, sizes

def term(nvector,n,p):
	"""
	this is function for finding the n'th term in the broken-bond model 
    for a given parameter vector and for a given direction
	"""
	if isinstance(nvector,numpy.ndarray):
		# normalize nvector
		x = nvector[:,0]/numpy.sqrt(numpy.sum(nvector**2,axis=1))
		y = nvector[:,1]/numpy.sqrt(numpy.sum(nvector**2,axis=1))
		z = nvector[:,2]/numpy.sqrt(numpy.sum(nvector**2,axis=1))
	elif isinstance(nvector, list):
		if len(nvector)==3:
			x=nvector[0]
			y=nvector[1]
			z=nvector[2]
			x = x/numpy.sqrt(x**2+y**2+z**2)
			y = y/numpy.sqrt(x**2+y**2+z**2)
			z = z/numpy.sqrt(x**2+y**2+z**2)
		else:
			print "index too long"
	else:
		print "index not list or numpy array, please change"
	#normalize nvector
	#print x, y, z
	if (n==0):
		return p*4* (abs(x+y) + abs(x-y) + abs(x+z) + abs(x-z) + abs(z+y) + abs(z-y))
	elif (n==1):
		return p*8*(abs(x)+abs(y)+abs(z))
	else:
		assert(n==2)
		return p*(abs(x+2*y+z) + abs(x+2*y-z) +abs(x-2*y+z) +abs(x-2*y-z) \
                       + abs(2*x+y+z) +abs(2*x+y-z) +abs(2*x-y+z) +abs(2*x-y-z)\
                       + abs(x+y+2*z) +abs(x+y-2*z) +abs(x-y+2*z) +abs(x-y-2*z))


def fitFunction(nvector,p,correction):
    #print "len(p) = ",len(p)
	# correction is n
	if correction:
		if (len(p)==1+correction):
			return term(nvector,0,p[0]) + corrections(nvector,p[1:])
		elif (len(p)==2+correction):
			return term(nvector,0,p[0]) + term(nvector,1,p[1])+corrections(nvector,p[2:])
		elif (len(p)==3+correction):
			return term(nvector,0,p[0]) + term(nvector,1,p[1]) + term(nvector,2,p[2])+corrections(nvector,p[3:])
		else:
			print "wrong number of parameters specified for fit"
			raise Exception
	else:
		if (len(p)==1):
			return term(nvector,0,p)
		elif (len(p)==2):
			return term(nvector,0,p[0]) + term(nvector,1,p[1])
		elif (len(p)==3):
			return term(nvector,0,p[0]) + term(nvector,1,p[1]) + term(nvector,2,p[2])
		else:
			print "wrong number of parameters specified for fit"
			raise Exception

def corrections(nvector,c):
	"""
	#return c*term(nvector,0,1.)**3. # step-step interaction
	#return c[0]*term(nvector,0,1.)**3. + c[1]*term(nvector,1,1.)**3. + c[2]*term(nvector,2,1.)**3.
	#return c[0]*term(nvector,0,1.)**3. + c[1]*term(nvector,1,1.)**3.
	#return c[0]*term(nvector,0,1.)**2 + c[1]*term(nvector,1,1.)**2 +c[2]*term(nvector,0,1.)*term(nvector,2,1.) + c[3]*term(nvector,0,1.)*term(nvector,1,1.) + c[4]*term(nvector,0,1.)*term(nvector,2,1.)+c[5]*term(nvector,1,1.)*term(nvector,2,1.) # mixed-step interactions
	#phi, theta = thetaphis(nvector) # spherical harmonics
	"""
	if isinstance(nvector, list) and len(nvector)==3:
		v = numpy.array(nvector)
		x = nvector[0]/numpy.sqrt(numpy.dot(v,v))
		y = nvector[1]/numpy.sqrt(numpy.dot(v,v))
		z = nvector[2]/numpy.sqrt(numpy.dot(v,v))		
	else:
		nvector_array = numpy.array(nvector)
		nvectornorms = [numpy.sqrt(numpy.dot(v,v)) for v in nvector_array]
		x = nvector_array[:,0]/nvectornorms
		y = nvector_array[:,1]/nvectornorms
		z = nvector_array[:,2]/nvectornorms
	
	return c[0]
	#return c[0]+c[1]*(x**4.+y**4.+z**4.)+c[2]*(x**2.*y**2.+y**2.*z**2.+x**2.*z**2.)
	#return abs(c[0]*sph_harm(0,0,theta,phi)+c[1]*sph_harm(-4,4,theta,phi)+c[2]*sph_harm(0,4,theta,phi)+c[3]*sph_harm(4,4,theta,phi))


def fitEnergiesFromFile(fileName, n=2, p0=[0.1,-0.2,0.01],correction=0, fit_unrelaxed=True):    

    indices, e_unrelaxed, e_relaxed, sizes = loadFileIntoLists(fileName)

    indices = np.array(indices)

    bfparams, cov_x, cost, range, max_error = fitSurfaceEnergies(indices,e_relaxed,n=n,p0=p0,correction=correction) 
       
    plotSubSet(indices,e_relaxed,[1,-1,0],[1,1,0],bfparams,correction=correction)	 
    plotSubSet(indices,e_relaxed,[1,-1,2],[1,1,0],bfparams,correction=correction)
    plotSubSet(indices,e_relaxed,[1,1,-1],[0,1,1],bfparams,correction=correction)

    output_rel = (bfparams, cov_x, cost, range, max_error)

    if fit_unrelaxed:           
        bfparams, cov_x, cost, range, max_error = fitSurfaceEnergies(indices,e_unrelaxed,n=n,p0=p0,correction=correction)
        plotSubSet(indices,e_unrelaxed,[1,-1,0],[1,1,0],bfparams,correction=correction)
        plotSubSet(indices,e_unrelaxed,[1,-1,2],[1,1,0],bfparams,correction=correction)
        plotSubSet(indices,e_unrelaxed,[1,1,-1],[0,1,1],bfparams,correction=correction)
        output_unrel = (bfparams, cov_x, cost, range, max_error)
        return output_rel, output_unrel
    else:
        return output_rel


def fitSurfaceEnergies(indices,energies,n=2,p0=[0.1,-0.2,0.01],correction=0):
    """
	this is to do a fit of all the indices in the file
	n is to set up to which neighbor...
    """
    bfparams, cov_x, output, mesg, ier= leastsq(residual,p0[0:n+correction],args=(indices,energies,correction),full_output=True)
    cost = numpy.sum(abs(residual(bfparams,indices,energies,correction)/energies))/len(indices)
    min_e = numpy.min(energies)
    max_e = numpy.max(energies)
    range = numpy.sum(abs(residual(bfparams,indices,energies,correction)/(max_e-min_e)))/len(indices)
    max_error = max(abs(residual(bfparams,indices,energies,correction))/energies)

    return bfparams, cov_x, cost, range, max_error


def setPlotOptions(labelsize=20,tickmajor=20,tickminor=10,markersize=10,legendsize=20,legendspacing=1.5,labelsizexy=16):
	"""
	set plot label size, tick size, line size, markersize
	"""

	pylab.rcdefaults()
	pylab.rcParams.update({'xtick.labelsize':labelsizexy,\
						   'xtick.major.size':tickmajor,\
                           'xtick.minor.size':tickminor,\
                           'ytick.labelsize':labelsizexy,\
                           'ytick.major.size':tickmajor,\
                           'ytick.minor.size':tickminor,\
                           'lines.markersize':markersize,\
                           'axes.labelsize':labelsize,\
                           'legend.fontsize':legendsize,\
                           'legend.columnspacing':legendspacing,\
                               })


def plotSubSet(indices, energies,index0,poleaxis,params,correction=0):
	"""
	make plot of a crystallographic zone index0	
	"""
	
	selected_fit_indices=[]
	angles=[]
	angles_dict={}
	selected_energies = []

	for i in range(0,len(indices)):
		index = indices[i]
		index = list(index)
		[h,k,l] = index
		n_vector = numpy.array([h,k,l])/numpy.sqrt(h**2+k**2+l**2)
		energy = energies[i]
		if numpy.dot(index,index0)==0:
			angle = 2.**numpy.arccos(numpy.dot(poleaxis,[h,k,l])/(numpy.sqrt((h**2+k**2+l**2)*numpy.dot(poleaxis,poleaxis))))*180/numpy.pi
			selected_fit_indices.append(list(n_vector))
			angles.append(angle)
			angles_dict[angle]=list(n_vector)	
			selected_energies.append(energy)
	# sort the fit_indices by angle, so that we can connect lines
	angles = sorted(angles_dict.keys())
	sorted_e=[]
	fit_e=[]
	residuals=[]
	for angle in angles:
		n_vector=angles_dict[angle]
		listindex=selected_fit_indices.index(n_vector)
		sorted_e.append(selected_energies[listindex])
		fit_e.append(fitFunction(n_vector,params,correction))
		residuals.append(residual(params,n_vector,selected_energies[listindex],correction))
	
	pylab.figure()
	pylab.plot(angles,sorted_e,'bo',label='data')	
	pylab.plot(angles,fit_e,'r-',label='fit')
	pylab.xlabel("angle from "+str(poleaxis))
	pylab.ylabel(r"$eV/\AA^2$")
	pylab.title("surfaces perpendicular to "+str(index0),fontsize=20)
	pylab.legend(loc=0)
	#pylab.figure()
	#pylab.plot(angles,residuals)

	#pylab.show() 

def fitSubset(fileName,index0,poleaxis,n=2,p0=[0.1,-0.2,0.01],correction=0):
	"""
	to fit a subset of 
	surfaces perpendicular to index0
	"""

	indices, e_unrelaxed, e_relaxed, sizes = loadFileIntoLists(fileName)

	indices = numpy.array(indices)
	#errfunc = lambda p,x,y:(fitFunction(x,p)-y)

	selected_fit_indices=[]
	angles=[]
	angles_dict={}
	selected_e_unrel=[]
	selected_e_rel = []

	for i in range(0,len(indices)):
		index = indices[i,:]
		index = list(index)
		[h,k,l] = index
		n_vector = numpy.array([h,k,l])/numpy.sqrt(h**2+k**2+l**2)
		e_unrel = e_unrelaxed[i]
		e_rel = e_relaxed[i]
		if numpy.dot(index,index0)==0:
			angle = 2.**numpy.arccos(numpy.dot(poleaxis,[h,k,l])/(numpy.sqrt((h**2+k**2+l**2)*numpy.dot(poleaxis,poleaxis))))*180/numpy.pi
			selected_fit_indices.append(n_vector)
			angles.append(angle)
			angles_dict[angle]=n_vector	
			selected_e_unrel.append(e_unrel)
			selected_e_rel.append(e_rel)
	# somehow sort the fit_indices by angle
	selected_fit_indices = numpy.array(selected_fit_indices)
			
	output = leastsq(residual,p0[0:n+correction],args=(selected_fit_indices,selected_e_unrel,correction),full_output=True)
	output2 = leastsq(residual, p0[0:n+correction], args=(selected_fit_indices,selected_e_rel,correction),full_output=True)

	bfparams = output[0]
	bfparamsrel = output2[0]

	cost = numpy.sum(abs(residual(bfparamsrel,selected_fit_indices,selected_e_rel,correction))/selected_e_rel)/len(selected_fit_indices)
	min_e = numpy.min(selected_e_rel)
	max_e = numpy.max(selected_e_rel)
	perc_range = numpy.sum(abs(residual(bfparamsrel,selected_fit_indices,selected_e_rel,correction)/(max_e-min_e)))/len(selected_fit_indices)

	pylab.figure()
	#pylab.plot(angles,selected_e_unrel,'bo')
	#pylab.plot(angles,fitFunction(selected_fit_indices,bfparams,correction),'r+')
	pylab.plot(angles,selected_e_rel,'k+')
	pylab.plot(angles,fitFunction(selected_fit_indices,bfparamsrel,correction),'g^')
	pylab.figure()
	#pylab.plot(angles,residual(bfparams,selected_fit_indices,selected_e_unrel,correction)/selected_e_unrel,'r^')
	pylab.plot(angles,residual(bfparamsrel,selected_fit_indices,selected_e_rel,correction)/selected_e_rel,'k^')	

	#return bfparams, bfparamsrel
	return bfparamsrel, angles, selected_fit_indices
	#return bfparamsrel, cost, perc_range
	
def residualFuncAngle(fileName,bfparams,index0,poleaxis,correction=0):

	indices, e_unrelaxed, e_relaxed, sizes = loadFileIntoLists(fileName)

	indices = numpy.array(indices)

	selected_fit_indices=[]
	angle_from_min=[]
	angle_from_poleaxis=[]
	selected_e_unrel=[]
	selected_e_rel = []

	# first select list of indices along crystallographic zone
	for i in range(0,len(indices)):
		index = indices[i,:]
		index = list(index)
		e_unrel = e_unrelaxed[i]        
		e_rel = e_relaxed[i]
		if numpy.dot(index,index0)==0:
			selected_fit_indices.append(index)
			selected_e_unrel.append(e_unrel)
			selected_e_rel.append(e_rel)

	min_energy = min(selected_e_rel)
	min_index = selected_fit_indices[selected_e_rel.index(min_energy)]

	for index in selected_fit_indices:
		angle = numpy.arccos(numpy.dot(index,min_index)/(numpy.sqrt(numpy.dot(index,index)*numpy.dot(min_index,min_index))))*180/numpy.pi
		angle_from_min.append(angle)
		angle2 = numpy.arccos(numpy.dot(index,poleaxis)/(numpy.sqrt(numpy.dot(index,index)*numpy.dot(poleaxis,poleaxis))))*180/numpy.pi
		angle_from_poleaxis.append(angle2)

	selected_fit_indices = numpy.array(selected_fit_indices)
	selected_e_rel = numpy.array(selected_e_rel)

	pylab.figure()
	pylab.plot(angle_from_min, residual(bfparams,selected_fit_indices,selected_e_rel,correction),'bo')
	pylab.figure()
	pylab.plot(numpy.tan(numpy.array(angle_from_min)/180.*numpy.pi),residual(bfparams,selected_fit_indices,selected_e_rel,correction),'ro')
	pylab.figure() 
	pylab.plot(angle_from_poleaxis,selected_e_rel,'bo')

	#pylab.show()

	return angle_from_min,selected_fit_indices,angle_from_poleaxis 

def make2DGammaPlot(params,n=2,index0=[1,-1,0],poleaxis=[1,1,0],number_of_points=50):
	"""
	this is to make the gamma plot cross section using the fitted broken bond
	model
	"""
	
	thetas = numpy.linspace(0,2*numpy.pi,number_of_points)
	angles = []
	energies = []	
	phis = [] 

	for	theta in thetas:
		phi = scipy.optimize.fsolve(dotProduct,0.8,args=(theta,index0))[0]
		phis.append(phi)
		#print theta, phi	
		nvector = [sin(theta)*cos(phi),sin(theta)*sin(phi),cos(theta)]
		[h,k,l] = nvector
		energy = fitFunction(nvector,params)
		#energies.append(energy)
		angle = numpy.arccos(numpy.dot(poleaxis,[h,k,l])/(numpy.sqrt((h**2+k**2+l**2)*numpy.dot(poleaxis,poleaxis))))	
		if numpy.dot(numpy.cross([h,k,l],poleaxis),index0) < 0:
			angle = -1.0*angle
		#angles.append(angle)
		#print angle
		# plot with poleaxis pointing in +y direction
		exp_r = abs(0.2200912656713*sph_harm(0, 0,theta,phi) + 0.0032670284794418564*sph_harm(0, 4, theta, phi) + 0.00195264*(sph_harm(-4,4,theta,phi)+sph_harm(4,4,theta,phi))- 0.0023674865858444084*sph_harm(0, 6, theta, phi)+0.00442926*(sph_harm(4,6,theta,phi)+sph_harm(-4,6,theta,phi))-0.00211574*sph_harm(0,8,theta,phi)-0.000795321*(sph_harm(-4,8,theta,phi)+sph_harm(4,8,theta,phi))-0.0012122*(sph_harm(-8,8,theta,phi)+sph_harm(8,8,theta,phi)))
		pylab.plot(energy*sin(angle),energy*cos(angle),'r.')
		pylab.plot(exp_r*sin(angle),exp_r*cos(angle),'b.')

def dotProduct(phi,theta,nvector):
	return nvector[0]*sin(theta)*cos(phi)+nvector[1]*sin(theta)*sin(phi)+nvector[2]*cos(theta)
	

def residual(p,x,y,c):
	return (fitFunction(x,p,correction=c)-y)

def equilShape(element,params,size=(10,10,10),distance=25.0):
	"""
	this is to use the ratio of energies to calculate the equilibrium crystal shape, cycle through a bunch of (h,k,l) indices
	"""
	slab = FaceCenteredCubic(element,directions=([[1,0,0],[0,1,0],[0,0,1]]),size=(10,10,10))	
	energy100 = fitFunction([1,0,0],params)
	h100 = distance
	orig_positions = slab.get_positions()
	kept_positions = list(orig_positions)
	center = slab.get_center_of_mass()
	for h in range(-12,12):
		for k in range(0,9):
			for l in range(0,9):
				nvector=list([h,k,l]/numpy.sqrt(h**2+k**2+l**2))
				energyhkl = fitFunction(nvector,params)
				distancehkl = energyhkl/energy100*h100
				for i in range(0,len(kept_positions)):
					list_to_pop = []
					if numpy.dot(kept_positions[i],nvector) > distancehkl:
						list_to_pop.append(i)
				for i in list_to_pop:
					kept_positions.pop(i)
	
	# set up new slab with new positions
	number_of_atoms = len(kept_positions)
	elstring = str(number_of_atoms)+'Pt' 
	new_slab = Atoms(elstring,positions=kept_positions)

	return new_slab

def make3Dplot(indices,energies,params,sig_am=1/1000.,corrections=0):
	"""
	make a 3D plot of theoretical energies, and residuals saying how good the fit is
	"""
	
	dphi, dtheta = pi/250.0, pi/250.0
	[phi,theta] = numpy.mgrid[0:pi+dphi*1.5:dphi,0:2*pi+dtheta*1.5:dtheta]

	plottingindices = [cos(phi)*sin(theta),sin(phi)*sin(theta),cos(theta)]
	r = fitFunction(plottingindices,params,correction=corrections)
	x = r*cos(phi)*sin(theta)
	y = r*sin(phi)*sin(theta)
	z = r*cos(theta)

	#sph = mesh(x, y, z, color=(0.8,0.8,0.8), opacity=0.5)
	sph = mesh(x,y,z)

	xs = []
	ys = []
	zs = []
	res = []

	for i in range(0, len(indices)):
		[h,k,l]=indices[i]
		thein,phiin = radianangles(h,k,l)
		energ = energies[i]
		xs.append(energ*cos(phiin)*sin(thein))
		ys.append(energ*sin(phiin)*sin(thein))
		zs.append(energ*cos(thein))
		res.append(abs(energ - fitFunction([h,k,l],params,correction=corrections))/energ*sig_am) 

	print xs, ys, zs, res

	pts = points3d(xs,ys,zs,res)

	filestring = "SphereplotTest.obj"
	savefig(filestring)

	#show()

	return sph

def make_movie(indices,energies,params):
	"""
	this is to make a movie
	"""	
	sph=make3Dplot(indices,energies,params)
	s = gcf()

	# Make an animation:
	for i in range(72,144):
    	# Rotate the camera by 10 degrees.
		s.scene.camera.azimuth(5)
		# Resets the camera clipping plane so everything fits and then
    	# renders.
		s.scene.reset_zoom()
		# Save the scene.
		s.scene.save_png('animation/anim'+str(i).rjust(3,'0')+'.png')	
		print i
