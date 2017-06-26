#!/usr/bin/env python

import numpy
import os
import sys
import pyfits

from config import *
sys.path.append(qr_dir)

import podi_logging
import logging
import argparse


def collect_ccds(filelist, out_filename, bias=None):
    # print "--", "\n-- ".join(framelist[expid])

    primhdu = pyfits.PrimaryHDU()
    ccdlist = [primhdu]

    ccdlist_prep = {}
    for fn in filelist:
        logger.info("Reading and pre-reducing %s" % (fn))
        hdulist = pyfits.open(fn)

        #
        # Apply overscan subtraction
        #
        empty = numpy.empty(hdulist[0].data.shape, dtype=numpy.float32)
        empty[:,:] = numpy.NaN
        raw = hdulist[0].data
        hdr = hdulist[0].header
        for i in range(1,5):
            os_x1 = hdulist[0].header['T_OSMN%d1' % (i)]
            os_x2 = hdulist[0].header['T_OSMX%d1' % (i)]
            os_y1 = hdulist[0].header['T_OSMN%d1' % (i)]
            os_y2 = hdulist[0].header['T_OSMX%d2' % (i)]
            overscan_level = numpy.mean(raw[os_y1:os_y2, os_x1:os_x2])
            logger.debug("overscan %d: %4d..%4d %4d..%4d --> %.1f" % (i, os_x1, os_x2, os_y1, os_y2, overscan_level))

            im_x1 = hdr['T_EFMN%d1' % (i)]
            im_x2 = hdr['T_EFMX%d1' % (i)]
            im_y1 = hdr['T_EFMN%d2' % (i)]
            im_y2 = hdr['T_EFMX%d2' % (i)]
            empty[im_y1:im_y2, im_x1:im_x2] = raw[im_y1:im_y2, im_x1:im_x2] #- overscan_level

        #
        # Merge all single OTAs into a single, large MEF
        #

        det_id = hdulist[0].header['DET-ID']
        extname = "CCD.%03d" % (hdulist[0].header['DET-ID'])
        ccdlist_prep[extname] = pyfits.ImageHDU(
                data=empty,
                header=hdulist[0].header,
                name=extname
            )
        #sys.stdout.write(".")
        #sys.stdout.flush()

    #
    # Now take all CCDs and insert them into the final image, sorted by
    # distance from the center
    #
    ccd_order = [50, 49, 58, 41, 42, 57, 66, 33, 34, 65, 51, 48, 74, 25, 26,
                 73, 59, 43, 40, 56, 67, 35, 32, 64, 81, 18, 19, 80, 75, 27,
                 24, 72, 82, 20, 17, 79, 13, 86, 87, 12, 52, 47, 60, 44, 39,
                 55, 68, 36, 31, 63, 14, 85, 88, 11, 76, 28, 23, 71, 7, 93,
                 92, 6, 83, 21, 16, 78, 8, 94, 91, 5, 2, 98, 97, 1, 15, 84,
                 89, 53, 10, 46, 61, 45, 38, 54, 69, 37, 30, 62, 3, 99, 96,
                 0, 77, 29, 22, 9, 70, 95, 90, 4, 101, 103, 102, 100, 105, 111,
                 110, 104, 107, 109, 108, 106,]
    for _extname in ["CCD.%03d" % ccd for ccd in ccd_order][:16]:
        ccdlist.append(ccdlist_prep[_extname])
    out_hdulist = pyfits.HDUList(ccdlist)


    if (bias is not None):
        biashdu = pyfits.open(bias)

        for ext in out_hdulist:
            if (ext.name in biashdu and ext.data is not None):
                try:
                    ext.data -= biashdu[ext.name].data
                except:
                    print "An error occurred during bias subtraction for %s" % (ext.name)
                    pass

    #
    # All work done, write to file
    #
    if (out_filename is not None):
        out_hdulist.writeto(out_filename, clobber=True)

    return out_hdulist


if __name__ == "__main__":

    framelist = {}

    #
    # Handle all command line stuff
    #
    parser = argparse.ArgumentParser(
        description='Reduce Subaru-HSC frames.')
    parser.add_argument(
        'files', type=str, nargs='+', #nargs=1,
        metavar='input.fits',
        help='list of input files')
    parser.add_argument('--bias', dest='bias',
                        default=None, help='BIAS filename')
    parser.add_argument('--output', dest='output',
                        default=None, help='output filename')
    args = parser.parse_args()


    logsetup = podi_logging.setup_logging()
    logger = logging.getLogger("SubaruHSC")

    for fn in args.files:
        hdulist = pyfits.open(fn)

        expid = hdulist[0].header['EXP-ID']

        if (not expid in framelist):
            framelist[expid] = []
        
        framelist[expid].append(fn)
        hdulist.close()
        sys.stdout.write(".")
        sys.stdout.flush()



    for expid in framelist:
        logger.info("Working on exposure %s" % (expid))

        if (args.output is None):
            out_filename = "%s_comb.fits" % (expid)
        else:
            out_filename = args.output

        collect_ccds(framelist[expid], out_filename=out_filename,
                     bias=args.bias)

    podi_logging.shutdown_logging(logsetup)