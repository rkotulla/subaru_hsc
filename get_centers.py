#!/usr/bin/env python


import os
import sys
import pyfits
from astLib import astWCS
import numpy


if __name__ == "__main__":

    data = []

    for fn in sys.argv[1:]:

        hdulist = pyfits.open(fn)
        wcs = astWCS.WCS(hdulist[0].header, mode='pyfits')

        center = wcs.getCentreWCSCoords()

        # print fn, hdulist[0].header['T_CCDSN'], center[0], center[1]
        data.append([int(hdulist[0].header['DET-ID']), #T_CCDSN']),
                     float(center[0]),
                     float(center[1])])
        # T_CCDSN
    data = numpy.array(data)
    # print data
    # numpy.savetxt(sys.stdout, data)

    center_ra = numpy.median(data[:,1])
    center_dec = numpy.median(data[:,2])
    
    d = numpy.hypot( data[:,2]-center_dec,
                     (data[:,1]-center_ra)*numpy.cos(numpy.radians(center_dec)))


    sort = numpy.argsort(d)
    data_sorted = data[sort]
    
    data_full = numpy.append(data_sorted, d[sort].reshape((-1,1)), axis=1)
    numpy.savetxt(sys.stdout, data_full, fmt="%3d %.6f %.6f %.4f")

    print "#", center_ra, center_dec


    sorted_ccdtypes = data_sorted[:,0].astype(numpy.int)
    print "#",sorted_ccdtypes
    print len(sorted_ccdtypes)
    print len(set(sorted_ccdtypes))
