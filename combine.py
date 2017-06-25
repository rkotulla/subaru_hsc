#!/usr/bin/env python

import numpy
import os
import sys
import pyfits

from config import *
sys.path.append(qr_dir)

import podi_logging
import logging


def collect_ccds(filelist, out_filename):
    # print "--", "\n-- ".join(framelist[expid])

    primhdu = pyfits.PrimaryHDU()
    ccdlist = [primhdu]

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

        ccdlist.append(
            pyfits.ImageHDU(
                data=empty,
                header=hdulist[0].header,
                name="CCD.%03d" % (hdulist[0].header['DET-ID'])
            )
        )
        #sys.stdout.write(".")
        #sys.stdout.flush()

    #
    # All work done, write to file
    #
    out_hdulist = pyfits.HDUList(ccdlist)
    if (out_filename is not None):
        out_hdulist.writeto(out_filename, clobber=True)

    return out_hdulist


if __name__ == "__main__":

    framelist = {}

    logsetup = podi_logging.setup_logging()
    logger = logging.getLogger("SubaruHSC")

    for fn in sys.argv[1:]:
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

        out_filename = "%s_comb.fits" % (expid)
        collect_ccds(framelist[expid], out_filename=out_filename)

    podi_logging.shutdown_logging(logsetup)