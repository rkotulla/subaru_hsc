#!/usr/bin/env python

import os
import sys
import pyfits

import numpy
import scipy.optimize

import pyds9
import argparse
import astLib.astWCS as astWCS


def wcs_fit(p, wcs, headers, xy, radec, cos_dec):
    # update the WCS
    for i, key in enumerate(headers):
        wcs.header[key] = p[i]
    wcs.updateFromHeader()

    ra_dec = numpy.array(wcs.pix2wcs(xy[:,0], xy[:,1]))

    diff = (radec - ra_dec) * [cos_dec, 1.0]
    return diff.flatten()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Reduce Subaru-HSC frames.')

    parser.add_argument(
        'filename', type=str,
        metavar='input.fits',
        help='filename of input file')
    parser.add_argument(
        '--start', dest="start", type=int, default=1,
        help="number of extension to start with"
    )


    args = parser.parse_args()


    hdulist= pyfits.open(args.filename)
    hdulist.info()

    headers = ['CRPIX1', 'CRPIX2',
               'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2']
    #
    # open ds9
    #
    pyds9.ds9_xpans()
    ds9 = pyds9.DS9(target="subaru", start="-scale zscale -zoom 0.5", wait=25)

    for i_ext in range(args.start, len(hdulist)):
        ext = hdulist[i_ext]
        wcs = astWCS.WCS(ext.header, mode="pyfits")
        cos_dec = numpy.cos(numpy.radians(ext.header['CRVAL2']))
        datafile = "%sxx.%03d.wcsfix.cat" % (ext.header['EXP-ID'][:-2], ext.header['DET-ID'])

        center_ra, center_dec = wcs.getCentreWCSCoords()
        print center_ra, center_dec
        # display image in ds9
        pass

        # save current extension as separate file
        tmp_file = "tmp_%s.fits" % (ext.name)
        pyfits.PrimaryHDU(data=ext.data, header=ext.header).writeto(tmp_file, clobber=True)

        ds9.set("frame delete all")

        ds9.set("frame 1")
        ds9.set("wcs skyformat degrees")
        ds9.set("file %s" % (tmp_file))


        ds9.set("frame 2")
        ds9.set("wcs skyformat degrees")
        cmd = "dsssao coord %f %f degrees size 45 45 arcmin" % (center_ra, center_dec)
        print cmd
        ds9.set(cmd)
        ds9.set("dsssao close")


        ds9.set("frame 1")
        ds9.set("lock frame wcs")
        ds9.set("catalog 2mass")
        ds9.set("catalog close")
        #
        # Now get a set of point-pairs, the first indicating the position in
        # the image, the second one in the WCS system
        #
        all_pixel = []
        all_wcs = []

        if (os.path.isfile(datafile)):
            merged = numpy.loadtxt(datafile)
            print "Loading %d position from previous run" % (merged.shape[0])
            for i in range(merged.shape[0]):
                all_pixel.append(merged[i, 0:2])
                all_wcs.append(merged[i, 2:4])

        while (True):

            print "get position"
            _coords = ds9.get("imexam coordinate image")
            print _coords
            coords_px = [float(_coords.split()[0]), float(_coords.split()[1])]
            # print coords, coords_ali

            if (_coords == "0 0"):
                break


            _coords = ds9.get("imexam coordinate fk5")
            coords_wcs = [float(_coords.split()[0]), float(_coords.split()[1])]
            print _coords, coords_wcs

            # if (coords == "0 0"):
            #     break

            all_pixel.append(coords_px)
            all_wcs.append(coords_wcs)

        #
        # Now we have a full set of x/y and ra/dec pairs, modify the CD and
        # CRPIX values to match the WCS
        #
        all_pixel = numpy.array(all_pixel)
        all_wcs = numpy.array(all_wcs)

        p_init = [0] * len(headers)
        for i,key in enumerate(headers):
            p_init[i] = ext.header[key]

        print p_init

        fit = scipy.optimize.leastsq(wcs_fit,
                                 p_init,
                                 args=(wcs, headers, all_pixel, all_wcs, cos_dec),
                                 maxfev=1000,
                                 full_output=1)
        print fit
        improved_wcs = fit[0]

        #
        # Now update the header of the input image and save this CCD
        #
        for i,key in enumerate(headers):
            ext.header[key] = improved_wcs[i]

        tmp_file = "tmp_%s.wcsfix.fits" % (ext.name)
        pyfits.PrimaryHDU(data=ext.data, header=ext.header).writeto(tmp_file, clobber=True)

        # also save the user-generated position data
        merged = numpy.append(all_pixel, all_wcs, axis=1)
        numpy.savetxt(datafile, merged)


        next_ext = raw_input("next?")
        if (next_ext.lower() == "n"):
            break
